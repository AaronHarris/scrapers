$(function(){
	function randnum(num) {
		val = Math.random()*20;
		$("table tr td#v"+num).text(val);
	}
		
	function changenums(i) {
		str = "table tr td#v" + i;
		num = Math.random()*11;
		$(str).text(num);
	}

	function changerand() {
		num = Math.ceil(Math.random()*23);
		changenums(num);
	}

	for (var i = 1; i < 24; i++) {
		changenums(i);
	};

	for (var i = 0; i < 10000; i+=500) {
		setTimeout(changerand(), 1000+i);
	};

});