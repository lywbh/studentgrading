$(function() {
    showAllCourse();
});

function showAllCourse() {
    var data = getAllCourse();
    $('.courselist table tbody').empty();
    for(var i = 0, len = data.length; i < len; ++i) {
        var newtr = $('<tr></tr>');
        var newtd = $(
            '<td>' + data[i]['fields'].title + '</td>' +
            '<td>' + data[i]['fields'].year + data[i]['fields'].semester + '</td>' +
            '<td>' + data[i]['fields'].description + '</td>' +
            '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showCourseDetails(' + data[i]['pk'] + ')">详情</button>' + 
            '<form method="post" action="stuxls/" enctype="multipart/form-data"><input type="file" id="stuxls" name="stuxls"><input type="submit" name="submit"></form></td>'
        );
        newtr.append(newtd);
        $('.courselist table tbody').append(newtr);
    }
    $('.menu-opt li:eq(0)').addClass('active');
    $('.menu-opt li:eq(1)').removeClass('active');
}

function showCourseDetails(id) {
    var data = getCourse(id);
    if(data) {
        $('#course_id').val(data.id);
        $('#course_name').html(data.title);
        $('#course_date').html(data.year + data.semester);
        $('#course_description').html(data.description);
        $('#group_min').val(data.min_group_size);
        $('#group_max').val(data.max_group_size);
        $('#coursedetail').modal();
    }
}

function showAllStudent() {
    $.ajax({
       url: 'getallstudent?course_id=' + $('#course_id').val(),
       success: function(data) {
           console.log(data);
           $('#groupdetail table tbody').empty();
            for(var i = 0, len = data['content'].length; i < len; ++i) {
                var newtr = $('<tr></tr>');
                var newtd = $(
                    '<td>' + data['content'][i].s_id + '</td>' +
                    '<td>' + data['content'][i].name + '</td>' +
                    '<td>' + data['content'][i].s_class + '</td>'
                );
                newtr.append(newtd);
                $('#groupdetail table tbody').append(newtr);
            }
            $('#groupdetail').modal();
       },
       fail: function(data) {
           console.log(data);
       }
    });
}

function showAllGroup() {
    var data = getAllGroup($('#course_id').val());
    $('#groups table tbody').empty();
    if(data) {
        for(var i = 0, len = data['content'].length; i < len; ++i) {
            var newtr = $('<tr></tr>');
            var newtd = $(
                '<td>' + data['content'][i].number + '</td>' +
                '<td>' + data['content'][i].name + '</td>' +
                '<td>' + data['content'][i].leader + '</td>' +
                '<td>' + data['content'][i].contact + '</td>' +
                '<td></td>' +
                '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showGroup(' + "'" + data['content'][i].number + "'" + ')">详情</button></td>'
            );
            newtr.append(newtd);
            $('#groups table tbody').append(newtr);
        }
        $('#groups').modal();
    }
}

function showGroupConfig() {
    var course_id = $('#course_id').val();
    var data = getCourse(course_id);
    if(data) {
        $('#group_min').html(data.group_min);
        $('#group_max').html(data.group_max);
        $('#groupconfig').modal();
    }
}

function saveGroupConfig() {
    $.ajax({
       url: 'setgroupconfig/',
       type: 'POST',
       data: {
           course_id: $('#course_id').val(),
           group_min: $('#group_min').val(),
           group_max: $('#group_max').val()
       },
       success: function(data) {
           console.log(data);
           $('#groupconfig').modal('hide');
       },
       fail: function(data) {
           console.log(data);
       }
    });
}

function showGroup(group_id) {
    var course_id = $('#course_id').val();
    var data = getGroup(course_id, group_id);
    $('#groupdetail table tbody').empty();
    for(var i = 0, len = data['content'].length; i < len; ++i) {
        var newtr = $('<tr></tr>');
        var newtd = $(
            '<td>' + data['content'][i].s_id + '</td>' +
            '<td>' + data['content'][i].name + '</td>' +
            '<td>' + data['content'][i].s_class + '</td>'
        );
        newtr.append(newtd);
        $('#groupdetail table tbody').append(newtr);
    }
    $('#groupdetail').modal();
}

function saveCourse() {
    data = {
        title: $('#new_course_name').val(),
        year: $('#new_course_year').val(),
        semester: $('#new_course_semester').val(),
        description: $('#new_course_description').val()
    }
    var ret = newCourse(data);
    if(ret == 'success') {
        $('#newcourse').modal('hide');
        $('#new_course_name').val('');
        $('#new_course_year').val('');
        $('#new_course_semester').val('');
        $('#new_course_description').val('');
    }
}

function deleteCourse() {
    data = {id: $('#course_id').val()};
    var ret = delCourse(data);
    if(ret == 'success') {
        $('#coursedetail').modal('hide');
    }
}