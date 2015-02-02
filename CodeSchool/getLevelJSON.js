/*global saveAs, self*/
(function(view){
    var getLevelJSON = function() {
        return $('.level').map(function(){
            var $this = $(this);
            var obj = {};
            obj.title = $this.find('p.level-title').text().trim();
            obj.sublevels = $this.find('li .tct').map(function(){
                return $(this).text().trim();
            }).get();
            obj.urls = $('source[data-quality="hd"]').map(function(){return $(this).attr('src');}).get();
            return obj;
        }).get();
    };
    var getResources = function(){
        return $('ul .list-item').map(function(){
            var $this = $(this);
            var obj = {};
            obj.title = $this.text().trim();
            obj.url = $this.find('a').attr('href');
            return obj;
        }).get();
    }

    leveljson = getLevelJSON();
    var blob = new Blob([JSON.stringify(leveljson)], {type: "application/json;charset=utf-8"});
    saveAs(blob, "names.json");

})();
/*
$.map($('.course-title-link'), function(e){ console.log($(e).attr('href') + "\t" + $(e).text()) });
[
  {
    "title": "1 - The Sword of Syntax",
    "sublevels": [
      "Ternary Conditionals",
      "Logical Assignment I",
      "Logical Assignment II",
      "The Switch Block"
    ]
  },
  {
    "title": "2 - The Pendant of Performance",
    "sublevels": [
      "Loop Optimization",
      "Script Execution",
      "Short Performance Tips",
      "Measuring Performance I",
      "Measuring Performance II"
    ]
  },
  {
    "title": "3 - The Crystal of Caution",
    "sublevels": [
      "Careful Comparisons",
      "Exception Handling",
      "Stuff That (Sometimes) Sucks",
      "Number Nonsense"
    ]
  },
  {
    "title": "4 - The Mail of Modularity",
    "sublevels": [
      "Namespacing Basics",
      "Anonymous Closures",
      "Global Imports",
      "Augmentation"
    ]
  }
]

[
  "1.1 The Sword of Syntax - Ternary Conditionals",
  "1.2 The Sword of Syntax - Logical Assignment I",
  "1.3 The Sword of Syntax - Logical Assignment II",
  "1.4 The Sword of Syntax - The Switch Block",
  "2.1 The Pendant of Performance - Loop Optimization",
  "2.2 The Pendant of Performance - Script Execution",
  "2.3 The Pendant of Performance - Short Performance Tips",
  "2.4 The Pendant of Performance - Measuring Performance I",
  "2.5 The Pendant of Performance - Measuring Performance II",
  "3.1 The Crystal of Caution - Careful Comparisons",
  "3.2 The Crystal of Caution - Exception Handling",
  "3.3 The Crystal of Caution - Stuff That (Sometimes) Sucks",
  "3.4 The Crystal of Caution - Number Nonsense",
  "4.1 The Mail of Modularity - Namespacing Basics",
  "4.2 The Mail of Modularity - Anonymous Closures",
  "4.3 The Mail of Modularity - Global Imports",
  "4.4 The Mail of Modularity - Augmentation"
]
// doing this in python instead
function jsonToTitles(json) {
    var outarr = [];
    json.forEach(function(obj, index){
        var name = obj.title;
        obj.sublevels.forEach(function(sublevel,i){
            var str = name[0]+"."+(i+1)+name.substring(3);
            str += " - " + sublevel;
            outarr.push(str);
        });
    });
    return outarr;
} */

