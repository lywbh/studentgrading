$(function() {
    showAllCourse();
});

function showAllCourse() {
    $.ajax({
       url: '../../api/courses/giving/', 
       success: function(data) {
           console.log(data);
           $('.courselist table tbody').empty();
           for(var i = 0, len = data.length; i < len; ++i) {
               var newtr = $('<tr></tr>');
               var newtd = $(
                   '<td>' + data[i].title + '</td>' +
                   '<td>' + data[i].year + data[i].semester + '</td>' +
                   '<td>' + data[i].description + '</td>' +
                   '<td><form method="post" action="stuxls/?course_id=' + data[i].id + '" enctype="multipart/form-data"><input type="file" id="stuxls" name="stuxls"><input type="submit" name="submit"></form></td>'+ 
                   '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showCourseDetails(' + "'" + data[i].url + "'" + ')">详情</button></td>'
               );
               newtr.append(newtd);
               $('.courselist table tbody').append(newtr);
           }
           $('.courselist').show();
           $('.assignmentlist').hide();
           $('.menu-opt li:eq(0)').addClass('active');
           $('.menu-opt li:eq(1)').removeClass('active');
       },
       error: function(data){
           console.log(data);
       }
    });
}

function showCourseDetails(url) {
    $.ajax({
       url: url, 
       success: function(data) {
           console.log(data);
           $('#course_id').val(data.id);
           $('#course_name').html(data.title);
           $('#course_date').html(data.year + data.semester);
           $('#course_description').html(data.description);
           $('#c_course_description').val(data.description);
           $('#group_min').val(data.min_group_size);
           $('#group_max').val(data.max_group_size);
           $('#coursedetail').modal();
       },
       error: function(data){
           console.log(data);
       }
    });
}

function showAllStudent() {
    $.ajax({
       url: '../../api/courses/' + $('#course_id').val() + '/takes/',
       success: function(data) {
           console.log(data);
           $('#groupdetail table tbody').empty();
            for(var i = 0, len = data.length; i < len; ++i) {
                var stuinfo, s_class;
                $.ajax({
                    url: data[i].student,
                    async: false,
                    success: function(data) {
                        console.log(data);
                        stuinfo = data;
                    },
                    error: function(data) {
                        console.log(data);
                    }
                });
                $.ajax({
                    url: stuinfo.s_class,
                    async: false,
                    success: function(data) {
                        console.log(data);
                        s_class = data;
                    },
                    error: function(data) {
                        console.log(data);
                    }
                });
                var newtr = $('<tr></tr>');
                var newtd = $(
                    '<td>' + stuinfo.s_id + '</td>' +
                    '<td>' + stuinfo.name + '</td>' +
                    '<td>' + s_class.class_id + '</td>'
                );
                newtr.append(newtd);
                $('#groupdetail table tbody').append(newtr);
            }
            $('#groupdetail').modal();
       },
       error: function(data) {
           console.log(data);
       }
    });
}

function showAllGroup() {
    $.ajax({
       url: '../../api/courses/' + $('#course_id').val() + '/groups/',
       success: function(data) {
           console.log(data);
           $('#groups table tbody').empty();
            if(data) {
                for(var i = 0, len = data.length; i < len; ++i) {
                    var leader, contact;
                    $.ajax({
                       url: data[i].leader,
                       async: false,
                       success: function(data) {
                           console.log(data);
                           leader = data.name;
                       },
                       error: function(data) {
                           console.log(data);
                       }
                   });
                    var newtr = $('<tr></tr>');
                    var newtd = $(
                        '<td>' + data[i].number + '</td>' +
                        '<td>' + data[i].name + '</td>' +
                        '<td>' + leader + '</td>' +
                        '<td>' + data[i].contact + '</td>' +
                        '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showGroup(' + "'" + data[i].id + "'" + ')">组员</button></td>' +
                        '<td><button type="button" class="btn btn-danger btn-lg listbtn" data-toggle="modal" onclick="delGroup(' + "'" + data[i].id + "'" + ')">删除</button></td>'
                    );
                    newtr.append(newtd);
                    $('#groups table tbody').append(newtr);
                }
                $('#groups').modal();
            }
       },
       error: function(data) {
           console.log(data);
       }
    });
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
       url: '../../api/courses/' + $('#course_id').val() + '/',
       type: 'PATCH',
       data: {
           description: $('#c_course_description').val(),
           min_group_size: $('#group_min').val(),
           max_group_size: $('#group_max').val()
       },
       success: function(data) {
           console.log(data);
           $('#groupconfig').modal('hide');
           location.reload();
       },
       error: function(data) {
           console.log(data);
           alert(data.responseText);
       }
    });
}

function showGroup(group_id) {
    $.ajax({
       url: '../../api/courses/' + $('#course_id').val() + '/groups/' + group_id,
       success: function(data) {
           console.log(data);
           $('#groupdetail table tbody').empty();
            for(var i = 0, len = data.members.length; i < len; ++i) {
                var newtr = $('<tr></tr>');
                var newtd = $(
                    '<td>' + data[i].members.s_id + '</td>' +
                    '<td>' + data[i].members.name + '</td>' +
                    '<td>' + data[i].members.s_class + '</td>'
                );
                newtr.append(newtd);
                $('#groupdetail table tbody').append(newtr);
            }
            $('#groupdetail').modal();
       },
       error: function(data) {
           console.log(data);
       }
    });
}

function delGroup(group_id) {
    $.ajax({
       url: '../../api/groups/' + group_id,
       type: 'DELETE',
       success: function(data) {
           console.log(data);
           $('#groups').modal('hide');
           location.reload();
       },
       error: function(data) {
           console.log(data);
       }
    });
}

function saveCourse() {
    data = {
        title: $('#new_course_name').val(),
        year: $('#new_course_year').val(),
        semester: $('#new_course_semester').val(),
        description: $('#new_course_description').val()
    }
    $.ajax({
        url: '../../api/courses/',
        type: 'POST',
        data: data,
        success: function(data) {
            console.log(data);
            $('#newcourse').modal('hide');
            $('#new_course_name').val('');
            $('#new_course_year').val('');
            $('#new_course_semester').val('');
            $('#new_course_description').val('');
            location.reload();
        },
        error: function(data) {
            console.log(data);
            alert(data.responseText);
        }
    });
}

function deleteCourse() {
    $.ajax({
       url: '../../api/courses/' + $('#course_id').val(),
       type: 'DELETE',
       success: function(data) {
           console.log(data);
           $('#coursedetail').modal('hide');
           location.reload();
       },
       error: function(data) {
           console.log(data);
       }
    });
}

function showAllAssignment() {
    $.ajax({
       url: '../../api/courses/giving/', 
       success: function(data) {
           console.log(data);
           for(var i = 0, len = data.length; i < len; ++i) {
               $.ajax({
                   url: '../../api/assignments/?course=' + data[i].id,
                   success: function(data) {
                       console.log(data);
                       $('.assignmentlist table tbody').empty();
                       for(var j = 0, len = data.length; j < len; ++j) {
                           var course;
                           $.ajax({
                               url: data[j].course,
                               async: false,
                               success: function(data) {
                                   console.log(data);
                                   course = data;
                               },
                               error: function(data) {
                                   console.log(data);
                               }
                           });
                           var newtr = $('<tr></tr>');
                           var newtd = $(
                               '<td>' + course.title + '</td>' +
                               '<td>' + data[j].title + '</td>' +
                               '<td>' + data[j].description + '</td>' +
                               '<td>' + data[j].deadline + '</td>' +
                               '<td>' + data[j].grade_ratio + '</td>' +
                               '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showAssignmentsDetails(' + "'" + data[j].url + "'" + ')">编辑</button></td>'
                           );
                           newtr.append(newtd);
                           $('.assignmentlist table tbody').append(newtr);
                       }
                       $('.courselist').hide();
                       $('.assignmentlist').show();
                       $('.menu-opt li:eq(0)').removeClass('active');
                       $('.menu-opt li:eq(1)').addClass('active');
                   },
                   error: function(data) {
                       console.log(data);
                   }
               });
           }
       },
       error: function(data){
           console.log(data);
       }
    });
}

function showAssignmentsDetails(url) {
    $.ajax({
       url: url, 
       success: function(data) {
           console.log(data);
           $('#assignment_id').val(data.id);
           $('#assignment_dead_line').val('');
           $('#assignment_description').val('');
           $('#assignment_weight').val('');
           $('#assignmentdetail').modal();
       },
       error: function(data){
           console.log(data);
       }
    });
}

function saveAssignment() {
    $.ajax({
        url: '../../api/assignments/' + $('#assignment_id').val() + '/',
        type: 'PATCH',
        data: {
            deadline: $('#assignment_dead_line').val() + 'T00:00:00Z',
            description: $('#assignment_description').val(),
            grade_ratio: $('#assignment_weight').val()
        },
        success: function(data) {
            console.log(data);
            $('#assignmentdetail').modal('hide');
            location.reload();
        },
        error: function(data) {
            console.log(data);
            alert(data.responseText);
        }
    });
}

function newAssignment() {
    $.ajax({
        url: '../../api/courses/' + $('#course_id').val(),
        success: function(data) {
            console.log(data);
            $.ajax({
                url: '../../api/assignments/',
                type: 'POST',
                data: {
                    course: data.url,
                    title: $('#new_assignment_title').val(),
                    deadline: $('#new_assignment_dead_line').val() + 'T00:00:00Z',
                    description: $('#new_assignment_description').val(),
                    grade_ratio: $('#new_assignment_weight').val()
                },
                success: function(data) {
                    console.log(data);
                    $('#newassignment').modal('hide');
                    location.reload();
                },
                error: function(data) {
                    console.log(data);
                    alert(data.responseText);
                }
            });
        },
        error: function(data) {
            console.log(data);
        }
    });
}

function delAssignment() {
    $.ajax({
        url: '../../api/assignments/' + $('#assignment_id').val() + '/',
        type: 'DELETE',
        success: function(data) {
            console.log(data);
            $('#assignmentdetail').modal('hide');
            location.reload();
        },
        error: function(data) {
            console.log(data);
        }
    })
}