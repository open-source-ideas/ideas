// Get information about a specific issue
// Written by Fredrik August Madsen-Malmo (github@fredrikaugust)

var URL = "https://api.github.com/repos/mikaelbr/open-source-ideas/issues/" +
  (window.location.href).replace(/.+=/, '');

var xhr_issue_done = false;
var xhr_comments_done = false;

function remove_progress () {
  if (xhr_issue_done && xhr_comments_done) {
    $('.progress').slideUp();
  }
}

$(document).ready(function () {
  $.get({
    url: URL,
    success: function (data) {
      xhr_issue_done = true;
      remove_progress();
      document.title = data.title;
      $('#issue-title').html(data.title);
      $('#issue-a').attr('href', data.html_url);
      $('#issue-body').html(marked(data.body)
        .replace(/h[1-6]/g, 'h5')
        .replace('<img', "<img class='responsive-img'")
      );
    }
  });

  $.get({
    url: URL + '/comments',
    success: function (data) {
      xhr_comments_done = true;
      remove_progress();
      if (data.length === 0) {
        $('#comments').append('<i>No comments.</i>');
      }
      data.forEach(function (comment) {
        $('#comments').append(
          "<div class='col s12'><div class='card-panel'>" +
          "<strong>" + comment.user.login + "</strong><br>" +
          marked(comment.body)
            .replace('<img', "<img class='responsive-img'") +
          "</div></div>"
        );
      });
    }
  });
});
