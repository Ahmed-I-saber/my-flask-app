$(document).ready(function(){
    // تحميل قائمة الطلبة عند اختيار الصف
    $('#grade_select').change(function(){
        var grade = $(this).val();
        if(grade){
            $.getJSON("/get_students", { grade: grade }, function(data){
                var options = '<option value="">Select Student</option>';
                $.each(data, function(i, student){
                    options += '<option value="'+student.id+'">'+student.student_name+'</option>';
                });
                $('#student_select').html(options);
            });
        }
    });

    // عند اختيار طالب إعادة تحميل الصفحة مع تمرير معرف الطالب
    $('#student_select').change(function(){
        var student_id = $(this).val();
        if(student_id){
            window.location.href = "/dashboard?student_id=" + student_id;
        }
    });

    // زر مسح الحقول
    $('#clearFieldsBtn').click(function(){
        $('#studentForm')[0].reset();
    });

    // أزرار إضافة وتعديل الطالب
    $('#addStudentBtn').click(function(){
        $('#studentAction').val('add_student');
        $('#studentForm').submit();
    });
    $('#modifyStudentBtn').click(function(){
        $('#studentAction').val('modify_student');
        $('#studentForm').submit();
    });

    // تحميل قائمة المواد عند اختيار المنصة
    $('#platform').change(function(){
        var platform = $(this).val();
        if(platform){
            $.getJSON("/get_subjects", { platform: platform }, function(data){
                var options = '<option value="">Select Subject</option>';
                $.each(data, function(i, subject){
                    options += '<option value="'+subject.subject_name+'">'+subject.subject_name+'</option>';
                });
                $('#subject').html(options);
            });
        }
    });

    // تحميل قائمة المدرسين عند اختيار المادة
    $('#subject').change(function(){
        var subject = $(this).val();
        if(subject){
            $.getJSON("/get_teachers", { subject: subject }, function(data){
                var options = '<option value="">Select Teacher</option>';
                $.each(data, function(i, teacher){
                    options += '<option value="'+teacher+'">'+teacher+'</option>';
                });
                $('#teacher').html(options);
            });
        }
    });

    // دالة لتحميل بيانات التسجيلات للطالب المحدد
    function loadRegistrations(){
        var student_id = $('#student_id').val();
        if(student_id){
            $.getJSON("/get_registrations", { student_id: student_id }, function(data){
                var rows = '';
                $.each(data, function(i, reg){
                    rows += '<tr>';
                    rows += '<td>'+ reg.reg_id +'</td>';
                    rows += '<td>'+ reg.subject_name +'</td>';
                    rows += '<td>'+ reg.platform_name +'</td>';
                    rows += '<td>'+ reg.course_id +'</td>';
                    rows += '<td>'+
                            '<form method="POST" action="/dashboard" onsubmit="return confirm(\'Are you sure?\');">'+
                            '<input type="hidden" name="action" value="delete_registration">'+
                            '<input type="hidden" name="reg_id" value="'+ reg.reg_id +'">'+
                            '<button type="submit" class="btn btn-danger btn-sm">Delete</button>'+
                            '</form>'+
                            '</td>';
                    rows += '</tr>';
                });
                $('#registrationsTable tbody').html(rows);
            });
        }
    }

    // تحميل بيانات التسجيلات عند تحميل الصفحة
    loadRegistrations();
});
