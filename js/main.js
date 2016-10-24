// This is where the magic happens
// Written by Fredrik August Madsen-Malmo (github@fredrikaugust)

var URL = "https://api.github.com/repos/mikaelbr/open-source-ideas/issues";

function display_issues (flags = []) {
  $.get({
    url: URL,
    success: function (data) {
      show_issues_in_dom(data);
      $('.progress').slideUp();
    }
  });
}

function generate_label_html (labels) {
  var label_string = "";

  labels.forEach(function (label) {
    label_string += "<div class='chip'>" + label.name + "</div>";
  });

  return label_string;
}

function create_issue_url (issue) {
  var loc = window.location.href;
  if (loc.slice(-1) == '/') {
    return loc + 'issue.html?issue=' + issue;
  }
  return loc.replace(/\w+\.[^\.]+$/, '') + 'issue.html?issue=' + issue;
}

function show_issues_in_dom (issues) {
  issues.forEach(function (issue) {
    $('#cards .row').append(
      "<div class='col s12'>" +
      "<div class='card'>" +
      "<div class='card-content'>" +
      "<span class='card-title teal-text text-darken-4'>" +
      issue.title +
      "</span> " +
      generate_label_html(issue.labels) + "<p>" +
      remove_markdown(issue.body)
        .replace(/^Project description\s/, '') +
      "</p>" + "</div><div class='card-action'>" +
      "<a href='" + create_issue_url(issue.number) +
      "'>Read more</a>" +
      "<a target='_blank' href='" + issue.html_url + "'>View on GitHub</a>" +
      "</div></div></div>"
    );

  });
}

$(document).ready(function () {
  display_issues();
});
