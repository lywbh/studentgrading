$(function() {
    showAllCourse();
});

function showAllCourse() {
    var data = getAllCourse();
    $('.courselist table tbody').empty();
    console.log(data);
    for(var i = 0, len = data.length; i < len; ++i) {
        var newtr = $('<tr></tr>');
        var newtd = $(
            '<td>' + data[i]['fields'].course_name + '</td>' +
            '<td>' + data[i]['fields'].course_date + '</td>' +
            '<td>' + data[i]['fields'].course_description + '</td>' +
            '<td>' + data[i]['fields'].course_teacher + '</td>' +
            '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showCourseDetails(' + data[i]['pk'].course_id + ')">详情</button></td>'
        );
        newtr.append(newtd);
        $('.courselist table tbody').append(newtr);
    }
    $('.menu-opt li:eq(0)').addClass('active');
    $('.menu-opt li:eq(1)').removeClass('active');
}

function showCourseDetails(id) {
    var data = getCourse(id);
    console.log(data);
    if(data) {
        $('#course_id').val(data.course_id);
        $('#course_name').html(data.course_name);
        $('#course_date').html(data.course_date);
        $('#course_description').html(data.course_description);
        $('#course_teacher').html(data.course_teacher);
        $('#coursedetail').modal();
    }
}

function showGroupConfig() {
    var course_id = $('#course_id').val();
    var data = getCourse(course_id);
    if(data) {
        $('#group_prefix').html(data.group_prefix);
        $('#group_min').html(data.group_min);
        $('#group_max').html(data.group_max);
        $('#groupconfig').modal();
    }
}

function showAllGroup() {
    var course_id = $('#course_id').val();
    var data = getAllGroup(course_id);
    if(data) {
        $('#group_id').html(data.group_id);
        $('#group_name').html(data.group_name);
        $('#group_contact').html(data.group_contact);
        $('#groups').modal();
    }
}

function showGroup() {
    var course_id = $('#course_id').val();
    var group_id = $('#group_id').html();
    var data = getGroup(course_id, group_id);
    console.log(data);
    $('.groupdetail table tbody').empty();
    for(var i = 0, len = data.length; i < len; ++i) {
        var newtr = $('<tr></tr>');
        var newtd = $(
            '<td>' + data[i]['fields'].student_id + '</td>' +
            '<td>' + data[i]['fields'].student_name + '</td>' +
            '<td>' + data[i]['fields'].student_class + '</td>'
        );
        newtr.append(newtd);
        $('.groupdetail table tbody').append(newtr);
    }
    $("groupdetail").modal();
}

function saveCourse() {
    
}
