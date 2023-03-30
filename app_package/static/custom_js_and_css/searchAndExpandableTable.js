$(document).ready(function() {
  // Search functionality
  $("#search").on("keyup", function() {
    var value = $(this).val().toLowerCase();
    $("#myTable tbody tr").filter(function() {
      $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
    });
  });
  
  // Expandable rows
  $("#myTable tbody tr").each(function() {
    var $expandRow = $("<td class='expand-row' colspan='" + $(this).children().length + "'><div class='expand-content'>" + $(this).html() + "</div></td>");
    $(this).after($expandRow);
    $(this).addClass("clickable-row");
  });

  $(".clickable-row").click(function() {
    $(this).toggleClass("expanded");
  });
});
