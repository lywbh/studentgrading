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
            '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showCourseDetails(' + data[i]['pk'] + ')">详情</button></td>'
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
        $('#coursedetail').modal();
    }
}

function showMyGroup() {
    var course_id = $('#course_id').val();
    var data = getMyGroup(course_id);
    $('#mygroup table tbody').empty();
    for(var i = 0, len = data['content'].length; i < len; ++i) {
        var newtr = $('<tr></tr>');
        var newtd = $(
            '<td>' + data['content'][i].s_id + '</td>' +
            '<td>' + data['content'][i].name + '</td>' +
            '<td>' + data['content'][i].s_class + '</td>'
        );
        newtr.append(newtd);
        $('#mygroup table tbody').append(newtr);
    }
    $('#mygroup').modal();
}

function showNewGroup() {
    var course_id = $('#course_id').val();
    if(getMyGroup(course_id)) {
        alert("You've already joined a group!")
    }
    else{
        var data = getCandidateStudent(course_id);
        $('#newgroup #candidatelist').empty();
        $('#newgroup table tbody').empty();
        for(var i = 0, len = data['content'].length; i < len; ++i) {
            var newoption = $('<option value="' + data['content'][i].s_id + '">' + data['content'][i].name + '</option>');
            $('#newgroup #candidatelist').append(newoption);
        }
    }
    $('#newgroup').modal();
}

function addMember() {
    var id = $("#candidatelist option:selected").val();
    var name = $("#candidatelist option:selected").text();
    var newtr = $(
        '<tr><td>' + id + 
        '</td><td>' + name +
        '</td><td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="delMember(' + id + ', ' + name + ')">删除</button></td></tr>'
    );
    $('#newgroup #candidatelist').remove('option[value=' + $("#candidatelist option:selected").val() + ']');
    $('#newgroup table tbody').append(newtr);
}

function delMember(id, name) {
    var newoption = $('<option value="' + id + '">' + name + '</option>');
    $('#newgroup #candidatelist').append(newoption);
    $('#newgroup table tbody tr').each(function() {
        if($(this).children().eq(0).html() == id) {
            $(this).remove();
        }
    });
}

function saveGroup() {
    
}