$(function(){
	fontSize();
	$(window).on('resize', function(){
		fontSize();
	});
});

function fontSize(){
	var winW = $(window).width();
	var fontsize = winW / 20;
	if(winW >= 320){
		$('html').css('font-size',fontsize);
	}
}