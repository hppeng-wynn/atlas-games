let url = "https://media.discordapp.net/attachments/662775844032348171/872287608061952062/unknown.png?width=735&height=613";

// Let's create a mock visualization
var width = 735*2, height = 613*2;
var circleSizeMax = 15;
var rMax = Math.min(width,height)/2 - circleSizeMax;

var radius 	= d3.scale.linear().range([0,rMax]);
var angle 	= d3.scale.linear().range([0,2*Math.PI]);
var size 	= d3.scale.linear().range([0,circleSizeMax]);
var color 	= d3.scale.ordinal().range(['#fcfb3c','#fcf900','#ff825a','#ffd2cb','#71d362','#ffd16f','#ff3d5d','#ff7218','#04b3f3','#bce5ac','#6e0215','#69D2E7','#A7DBDB','#E0E4CC','#F38630','#E94C6F','#542733','#5A6A62','#C6D5CD','#DB3340','#E8B71A','#F7EAC8','#1FDA9A','#588C73','#F2E394','#F2AE72','#D96459','#D0C91F','#85C4B9','#008BBA','#DF514C','#00C8F8','#59C4C5','#FFC33C','#FBE2B4','#5E412F','#FCEBB6','#78C0A8','#F07818','#DE4D4E','#DA4624','#DE593A','#FFD041','#B1EB00','#53BBF4','#FF85CB','#FF432E','#354458','#3A9AD9','#29ABA4','#E9E0D6','#4298B5','#ADC4CC','#92B06A','#E19D29','#BCCF02','#5BB12F','#73C5E1','#9B539C','#FFA200','#00A03E','#24A8AC','#0087CB','#260126','#59323C','#F2EEB3','#BFAF80','#BFF073','#0DC9F7','#7F7F7F','#F05B47','#3B3A35','#20457C','#5E3448','#FB6648','#E45F56','#A3D39C','#7ACCC8','#4AAAA5','#DC2742','#AFA577','#ABA918','#8BAD39','#F2671F','#C91B26','#9C0F5F','#60047A','#0F5959','#17A697','#638CA6','#8FD4D9','#83AA30','#1499D3','#4D6684','#3D3D3D','#333333','#424242','#00CCD6','#EFEFEF','#CCC51C','#FFE600','#F05A28','#B9006E','#F17D80','#737495','#68A8AD','#C4D4AF']);
var x = function(d) { return radius( d.r ) * Math.cos( angle( d.angle ) ); };
var y = function(d) { return radius( d.r ) * Math.sin( angle( d.angle ) ); };

var svg = d3.select('body').append('svg')
	.attr('width', width)
	.attr('height',height);

var chart = svg.append('g').attr('transform','translate('+[width/2,height/2]+')');

var image = svg.append("svg:image").attr('x', 0).attr('y', 0).attr('xlink:href', url);

var data = d3.range(150).map( function(d) { return {r: Math.random(), angle: Math.random(), size: Math.random() }; });

chart.selectAll('cirle')
	.data(data).enter()
	.append('circle')
	.attr('class','blendCircle')
	.attr({
		cx: x,
		cy: y,
		r: function(d) { return size(d.size); },
		fill: function(d,i) { return color(i); }
	});

function save_image() {
    let svg_string = getSVGString(svg.node());
    function display(blob, image) {
        document.body.appendChild(image);
    }
    svgString2Image( svg_string, width, height, "png", display );
}
