$(function() {
    showAllCourse();
});

function showAllCourse() {
    $.ajax({
       url: '../../api/courses/taking/', 
       success: function(data) {
           $('.courselist table tbody').empty();
           for(var i = 0, len = data.length; i < len; ++i) {
               var newtr = $('<tr></tr>');
               var newtd = $(
                   '<td>' + data[i].title + '</td>' +
                   '<td>' + data[i].year + data[i].semester + '</td>' +
                   '<td>' + data[i].description + '</td>' +
                   '<td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="showCourseDetails(' + "'" + data[i].url + "'" + ')">详情</button></td>'
               );
               newtr.append(newtd);
               $('.courselist table tbody').append(newtr);
           }
           $('.menu-opt li:eq(0)').addClass('active');
           $('.menu-opt li:eq(1)').removeClass('active');
       },
       error: function(data){
       }
    });
}

function showCourseDetails(url) {
    $.ajax({
       url: url, 
       success: function(data) {
           $('#course_id').val(data.id);
           $('#course_name').html(data.title);
           $('#course_date').html(data.year + data.semester);
           $('#course_description').html(data.description);
           $('#coursedetail').modal();
       },
       error: function(data){
       }
    });
}

function showMyGroup() {
    $.ajax({
        url: '../../api/myself/',
        success: function(data) {
            $.ajax({
                url: data.url,
                success: function(data) {
                    $.ajax({
                       url: '../../api/groups/?course=' + $('#course_id').val() + '&has_student=' + data.id,
                       success: function(data) {
                           if(data.length == 0) {
                               alert("You are not in a group!")
                           }
                           else if(data.length == 1) {
                               $('#mygroup table tbody').empty();
                               $.ajax({
                                   url: data[0].leader,
                                   async: false,
                                   success: function(data) {
                                       var s_class;
                                       $.ajax({
                                           url: data.s_class,
                                           async: false,
                                           success: function(data) {
                                               s_class = data;
                                           },
                                           fail: function(data) {
                                           }
                                       });
                                       var newtr = $('<tr></tr>');
                                       var newtd = $(
                                           '<td>' + data.s_id + '</td>' +
                                           '<td>' + data.name + '</td>' +
                                           '<td>' + s_class.class_id + '</td>'
                                       );
                                       newtr.append(newtd);
                                       $('#mygroup table tbody').append(newtr);
                                   },
                                   fail: function(data) {
                                   }
                               });
                               for(var i = 0, len = data[0].members.length; i < len; ++i) {
                                   var member;
                                   $.ajax({
                                      url: data[0].members[i],
                                      async: false,
                                      success: function(data) {
                                          member = data;
                                      },
                                      fail: function(data) {
                                      }
                                   });
                                   var s_class;
                                   if(member.s_id && member.s_class) {
                                       $.ajax({
                                          url: member.s_class,
                                          async: false,
                                          success: function(data) {
                                              s_class = data;
                                          },
                                          fail: function(data) {
                                          }
                                       });
                                       var newtr = $('<tr></tr>');
                                       var newtd = $(
                                           '<td>' + member.s_id + '</td>' +
                                           '<td>' + member.name + '</td>' +
                                           '<td>' + s_class.class_id + '</td>'
                                       );
                                       newtr.append(newtd);
                                   }
                                   else{
                                       s_class = undefined;
                                       var newtr = $('<tr></tr>');
                                       var newtd = $(
                                           '<td></td>' +
                                           '<td>' + member.name + '</td>' +
                                           '<td></td>'
                                       );
                                       newtr.append(newtd);
                                   }
                                   $('#mygroup table tbody').append(newtr);
                               }
                               $('#mygroup').modal();
                           }
                           else{
                           }
                       },
                       error: function(data) {
                       }
                    });
                },
                error: function(data) {
                }
            });
        },
        error: function(data) {
        }
    });
}

function showNewGroup() {
    $.ajax({
        url: '../../api/myself/',
        success: function(data) {
            var self_id;
            $.ajax({
                url: data.url,
                success: function(data) {
                    self_id = data.id;
                    $.ajax({
                       url: '../../api/groups/?course=' + $('#course_id').val() + '&has_student=' + data.id,
                       success: function(data) {
                           if(data.length == 0) {
                               $.ajax({
                                   url: '../../api/students/?course=' + $('#course_id').val() + '&grouped=False',
                                   success: function(data) {
                                       $('#newgroup #candidatelist').empty();
                                       $('#newgroup table tbody').empty();
                                       for(var i = 0, len = data.length; i < len; ++i) {
                                           if(data[i].id !== self_id) {
                                               var newoption = $('<option value="' + data[i].id + '" url="' + data[i].url + '">' + data[i].name + '</span></option>');
                                               $('#newgroup #candidatelist').append(newoption);
                                           }
                                       }
                                       $('#newgroup').modal();
                                   },
                                   error: function(data) {
                                   }
                               });
                           }
                           else{
                               alert("You've already joined a group!")
                           }
                       },
                       error: function(data) {
                       }
                    });
                },
                error: function(data) {
                }
            });
        },
        error: function(data) {
        }
    });
}

function addMember() {
    if($('#newgroup #candidatelist').html()) {
        var id = $("#candidatelist option:selected").val();
        var name = $("#candidatelist option:selected").text();
        var url = $("#candidatelist option:selected").attr("url");
        var newtr = $(
            '<tr><td>' + id + 
            '</td><td>' + name +
            '</td><td style="display:none">' + url +
            '</td><td><button type="button" class="btn btn-primary btn-lg listbtn" data-toggle="modal" onclick="delMember(' + id + ", '" + name + "', '" + url + "'" + ')">删除</button></td></tr>'
        );
        $('#candidatelist option[value=' + id + ']').remove();
        $('#newgroup table tbody').append(newtr);
    }   
}

function delMember(id, name, url) {
    var newoption = $('<option value="' + id + '" url="' + url + '">' + name + '</option>');
    $('#newgroup #candidatelist').append(newoption);
    $('#newgroup table tbody tr').each(function() {
        if($(this).children().eq(0).html() == id) {
            $(this).remove();
        }
    });
}

function saveGroup() {
    var members = [];
    $('#newgroup table tbody tr').each(function() {
        members.push($(this).children().eq(2).html());
    });
    $.ajax({
        url: '../../api/myself/',
        success: function(data) {
            $.ajax({
                url: '../../api/courses/' + $('#course_id').val() + '/add_group/',
                type: 'POST',
                data: $.param({
                    name: $('#new_group_name').val(),
                    leader: data.url,
                    members: members
                }, true),
                success: function(data) {
                    $('#newgroup').modal('hide');
                },
                error: function(data) {
                }
            });
        },
        error: function(data) {
            alert(data.responseText);
        }
    });
}