function getAllCourse() {
    var ret;
    $.ajax({
       url: 'getcourse',
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function getCourse(id) {
    var ret;
    $.ajax({
       url: 'getcourse?id=' + id,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function getAllGroup(course_id) {
    var ret;
    $.ajax({
       url: 'getgroup?course_id=' + course_id,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function getGroup(course_id, group_id) {
    var ret;
    $.ajax({
       url: 'getgroup?course_id=' + course_id + '&group_id=' + group_id,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function getMyGroup(course_id) {
    var ret;
    $.ajax({
       url: 'getgroup?course_id=' + course_id,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function newCourse(data) {
    var ret;
    $.ajax({
       url: 'newcourse/',
       type: 'POST',
       data: data,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}

function delCourse(data) {
    var ret;
    $.ajax({
       url: 'delcourse/',
       type: 'POST',
       data: data,
       async: false,
       success: function(data) {
           console.log(data);
           ret = data;
       },
       fail: function(data) {
           console.log(data);
       }
    });
    return ret;
}