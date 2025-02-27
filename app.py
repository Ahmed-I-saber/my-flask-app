from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"  # تأكد من تعيين مفتاح سري مناسب

# دالة الاتصال بقاعدة البيانات مع تجميع الاتصالات
def get_db_connection():
    return mysql.connector.connect(
        pool_name="mypool",
        pool_size=5,
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "ahmed"),
        password=os.environ.get("DB_PASSWORD", "password"),
        database=os.environ.get("DB_NAME", "SchoolDB"),
        ssl_disabled=True
    )



#############################
# طريقة الترخيص
#############################
def initialize_license_table():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                license_key VARCHAR(255) UNIQUE NOT NULL,
                expiration_date DATE NOT NULL,
                active TINYINT(1) DEFAULT 1
            )
        ''')
        conn.commit()
    except mysql.connector.Error as e:
        print(f"Error initializing license table: {e}")
    finally:
        cursor.close()
        conn.close()

initialize_license_table()

def check_license():
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT expiration_date 
            FROM licenses 
            WHERE active = 1 
              AND expiration_date >= CURDATE() 
            LIMIT 1
        """)
        result = cursor.fetchone()
        return result is not None
    except mysql.connector.Error as e:
        print(f"Error checking license: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def validate_license_key(key):
    # قائمة المفاتيح الصالحة (يتم تحديثها يدويًا أو من API)
    valid_keys = ["VeP-1234-5678-90012", "TES1-0000-0000-0000"]
    if key in valid_keys:
        expiration_date = datetime.now() + timedelta(days=300)
        expiration_date_str = expiration_date.strftime("%Y-%m-%d")
        conn = get_db_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            # تعطيل كل التراخيص القديمة
            cursor.execute("UPDATE licenses SET active = 0")
            # إدخال الترخيص الجديد وتفعيله
            cursor.execute('''
                INSERT INTO licenses (license_key, expiration_date, active)
                VALUES (%s, %s, 1)
            ''', (key, expiration_date_str))
            conn.commit()
            return True
        except mysql.connector.IntegrityError:
            print("This license key has already been used.")
            return False
        except mysql.connector.Error as e:
            print(f"Error validating license key: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

@app.route("/activate_license", methods=["GET", "POST"])
def activate_license():
    if request.method == "POST":
        license_key = request.form.get("license_key", "").strip()
        if validate_license_key(license_key):
            flash("License activated successfully!", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid License Key.", "danger")
    return render_template("activate_license.html")

# التحقق من الترخيص قبل كل طلب (باستثناء صفحات الترخيص والملفات الثابتة)
@app.before_request
def require_license():
    if request.endpoint in ['activate_license', 'static']:
        return
    if not check_license():
        return redirect(url_for("activate_license"))

#############################
# بقية التطبيق (دوال تسجيل الدخول، اللوحة، AJAX ... إلخ)
#############################

# صفحة تسجيل الدخول
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        national_id = request.form.get("national_id", "").strip()
        if not national_id:
            flash("Please enter National ID.", "danger")
            return redirect(url_for("login"))
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Students WHERE national_id = %s", (national_id,))
            student = cursor.fetchone()
            cursor.close()
            conn.close()
            if student:
                session["student_id"] = student["id"]
                return redirect(url_for("dashboard"))
            else:
                flash("Student not found.", "danger")
        except Exception as e:
            flash(str(e), "danger")
    return render_template("login.html")

# لوحة تحكم الطالب وإدارة التسجيلات
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "student_id" not in session:
        return redirect(url_for("login"))
    student_id = session["student_id"]
    # جلب بيانات الطالب
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(str(e), "danger")
        student = {}
    
    # جلب التسجيلات الخاصة بالطالب مع جلب اسم المدرس (إن وجد)
    registrations = []
    total_price = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT r.id as reg_id, s.subject_name, p.platform_name, s.price, r.course_id, 
                   COALESCE(t.teacher_name, 'External') AS teacher_name
            FROM Registrations r
            JOIN Subjects s ON r.subject_id = s.id
            JOIN Platforms p ON r.platform_id = p.id
            LEFT JOIN Teachers t ON r.teacher_id = t.id
            WHERE r.student_id = %s
        """
        cursor.execute(query, (student_id,))
        registrations = cursor.fetchall()
        for reg in registrations:
            try:
                total_price += float(reg.get("price", 0))
            except:
                pass
        cursor.close()
        conn.close()
    except Exception as e:
        flash(str(e), "danger")
    
    # جلب بيانات المنصات
    platforms = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, platform_name FROM Platforms")
        platforms = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(str(e), "danger")
    
    # جلب الكورسات النشطة
    courses = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, course_name FROM courses WHERE course_status = 'Active'")
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(str(e), "danger")
    
    printed = student.get("printed") if student else 0
    return render_template("dashboard.html", student=student, registrations=registrations,
                           total_price=total_price, platforms=platforms, courses=courses,
                           printed=printed)

# نقطة نهاية لاسترجاع المواد التابعة لمنصة محددة (لاستدعاء AJAX)
@app.route("/get_subjects")
def get_subjects():
    platform_id = request.args.get("platform_id")
    if not platform_id:
        return jsonify([])
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, subject_name, price, teacher_id FROM Subjects WHERE platform_id = %s"
        cursor.execute(query, (platform_id,))
        subjects = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(subjects)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# نقطة نهاية لاسترجاع المدرسين تبعاً للمادة المحددة (يمكن تعديل العلاقة حسب هيكل قاعدة البيانات)
@app.route("/get_teachers")
def get_teachers():
    subject_id = request.args.get("subject_id")
    if not subject_id:
        return jsonify([])
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT teacher_id FROM Subjects WHERE id = %s", (subject_id,))
        subject = cursor.fetchone()
        teachers = []
        if subject and subject.get("teacher_id"):
            teacher_id = subject["teacher_id"]
            cursor.execute("SELECT id, teacher_name FROM Teachers WHERE id = %s", (teacher_id,))
            teacher = cursor.fetchone()
            if teacher:
                teachers.append(teacher)
        cursor.close()
        conn.close()
        teachers.append({"id": 0, "teacher_name": "External"})
        return jsonify(teachers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# حفظ تسجيل مادة جديدة
@app.route("/save_registration", methods=["POST"])
def save_registration():
    if "student_id" not in session:
        return redirect(url_for("login"))
    student_id = session["student_id"]
    subject_id = request.form.get("subject_id")
    platform_id = request.form.get("platform_id")
    teacher_id = request.form.get("teacher_id")
    course_id = request.form.get("course_id")
    times = request.form.get("times")
    if not all([subject_id, platform_id, teacher_id, course_id, times]):
        flash("Please fill all registration fields.", "danger")
        return redirect(url_for("dashboard"))
    try:
        times_int = int(times)
    except ValueError:
        flash("Times Registered must be an integer.", "danger")
        return redirect(url_for("dashboard"))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO Registrations (student_id, subject_id, platform_id, teacher_id, course_id, times_studied)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (student_id, subject_id, platform_id, teacher_id, course_id, times_int))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration saved successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("dashboard"))

# حذف تسجيل مادة
@app.route("/delete_registration/<int:reg_id>")
def delete_registration(reg_id):
    if "student_id" not in session:
        return redirect(url_for("login"))
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Registrations WHERE id = %s", (reg_id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registration deleted successfully.", "success")
    except Exception as e:
        flash(str(e), "danger")
    return redirect(url_for("dashboard"))

# تحديد كورس للطباعة
@app.route("/print_registration", methods=["GET", "POST"])
def print_registration():
    if "student_id" not in session:
        return redirect(url_for("login"))
    student_id = session["student_id"]
    if request.method == "POST":
        course_id = request.form.get("course_id")
        if not course_id:
            flash("Please select a course.", "danger")
            return redirect(url_for("print_registration"))
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE Students SET printed = 1 WHERE id = %s", (student_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            flash(str(e), "danger")
        student = {}
        registrations = []
        total_price = 0
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Students WHERE id = %s", (student_id,))
            student = cursor.fetchone()
            query = """
                SELECT r.id as reg_id, s.subject_name, p.platform_name, s.price, r.course_id, 
                       COALESCE(t.teacher_name, 'External') AS teacher_name
                FROM Registrations r
                JOIN Subjects s ON r.subject_id = s.id
                JOIN Platforms p ON r.platform_id = p.id
                LEFT JOIN Teachers t ON r.teacher_id = t.id
                WHERE r.student_id = %s AND r.course_id = %s
            """
            cursor.execute(query, (student_id, course_id))
            registrations = cursor.fetchall()
            for reg in registrations:
                try:
                    total_price += float(reg.get("price", 0))
                except:
                    pass
            cursor.close()
            conn.close()
        except Exception as e:
            flash(str(e), "danger")
        return render_template("print.html", student=student, registrations=registrations, total_price=total_price)
    else:
        courses = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT DISTINCT r.course_id, c.course_name
                FROM Registrations r
                JOIN courses c ON r.course_id = c.id
                WHERE r.student_id = %s
            """
            cursor.execute(query, (student_id,))
            courses = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            flash(str(e), "danger")
        return render_template("select_course.html", courses=courses)

if __name__ == "__main__":
    app.run(port=5001, debug=True)
