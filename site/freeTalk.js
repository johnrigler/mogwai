f = new Array();
f.abi = new Array();

polygon = new Array();
polygon.jethro = new Array();

// metis = new Array();
// metis.jethro = new Array();

f.abi.jethro = [{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"stateMutability":"payable","type":"fallback"},{"inputs":[{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"cashout","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"string","name":"","type":"string"}],"name":"map","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"artifact","type":"string"},{"internalType":"string","name":"body","type":"string"}],"name":"mapArtifact","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"message1","type":"string"},{"internalType":"string","name":"message2","type":"string"},{"internalType":"address[]","name":"index","type":"address[]"}],"name":"tell","outputs":[],"stateMutability":"payable","type":"function"},{"stateMutability":"payable","type":"receive"}]

polygon.jethro.address = "0x0076416C84c7151CaEfA74C3e09d6eBF2f296BA0";
polygon.provider = ethers.getDefaultProvider(137);
polygon.jethro.contract = new ethers.Contract(polygon.jethro.address,f.abi.jethro,polygon.provider);

// metis.jethro.address = "0x218F42C8c226a76C29C6c8C9a4814b48996Cf642";
// metis.api="https://andromeda-explorer.metis.io/api?module=account&action=txlist&address=" + metis.jethro.address;

//metis.provider = ethers.getDefaultProvider(1088);
//metis.jethro.contract = new ethers.Contract(metis.jethro.address,jethro.abi,metis.provider);


//if(window.ethereum != null)
//{
  // f.metamask = new ethers.BrowserProvider(window.ethereum);
 //  polygon.metamaskJethro = new ethers.Contract(polygon.jethro.address,f.abi.jethro,f.metamask.getSigner());
////   metis.metamaskJethro = new ethers.Contract(metis.jethro.address,jethro.abi,f.metamask.getSigner());
//}

f.utils = new Array();


// This uses a number of objects. magicHydrator is hard-coded to "f", even though it
// is stored in Jethro. If I update it, then I will likely move it from "f". 

// Load magicHydrator (will need to eval later)
//

console.log("39", polygon.jethro.contract);

var stage = "a";

function stageA() {
if(typeof(f.note) == 'object') 
  {
  f.noteAPI="https://rigler.org/note/";
  console.log(f.note);
  return "b";
  }  
  else return "a";
}


function stageB() {

console.log(f.note)

if(typeof(f.note.read) == "function")
          {
     //     console.log(f.noteAPI);
          f.note.read("GUI.magic").then( x => f.GUI = (f.utils.magicHydrator("GUI",x) ));
          return "c";
          }

if(typeof(GUI) == "object") return "c";

return "b";

}

function stageC() {
if(typeof(f.GUI) === "string") return "d"; 

return "c";
}

function stageE() {

GUI.drawHome("header");
GUI.drawScanner("header");
GUI.drawEval("header");

return "f";

}



async function myLoop() {

for(x = 0; x < 100; x++)
   {
   await f.utils.sleep(5000);
   if(typeof(middle) == "object")
        {
        if(typeof(polygon.jethro.contract.map) == 'function')
	  if(typeof(f.utils.magicHydrator) == 'function')
            {
            if(typeof(f.note) == 'object')
                 { 
		    if(stage === "a") stage = stageA(); 
		    if(stage === "b") stage = stageB();
                    if(stage === "c") { stage = stageC(); };
		    if(stage === "d") 
                          { 
		          eval(f.GUI); 
                           stage = "e";
	                  }
                    if(stage === "e")
                        {
                        stage = stageE();
		        x = 100;
		        middle.innerHTML = "";
	                break;
	                }
                  }
	     else
		polygon.jethro.contract.map("f.note").then( x => eval(x) )

	    middle.innerHTML += ".";
	    if(x % 10 == 0)middle.innerHTML += "<br>";
	    continue;
            }
            else
            {
            polygon.jethro.contract.map("magicHydrator").then( x =>
               { 
               eval(x)
               f.utils.magicHydrator = magicHydrator;
//               f.note.read("GUI.magic").then( x => { magicHydrator("GUI",x) ; console.log("GUI", GUI) });
               })

	    middle.innerHTML += "."; 
            }
        }
   }
}




/*
polygon.jethro.contract.map("magicHydrator").then( x => 
    { 
    eval(x)
    f.utils.magicHydrator = magicHydrator;
    f.note.read("GUI.magic").then( x => { magicHydrator("GUI",x) ; console.log("GUI", GUI) });
    })
*/

// f.contract = polygon.jethro.contract;
//



f.utils.delayLoad = async function delayLoad() { 
  await f.utils.sleep(8000); // Sleep for 2 seconds 
//    eval(f.utils.magicHydrator); 
  //  f.utils.magicHydrator = magicHydrator;
//    await f.utils.sleep(2000);
//    f.note.read("GUI.magic").then( x => eval(f.utils.magicHydrator("GUI",x)) )
  await f.utils.sleep(8000);
//    console.log(GUI.drawHome.toString());
//    GUI.drawHome( "header" );
//    GUI.drawGomez( "header" );
//    GUI.drawScanner( "header" );
//    GUI.drawEval( "header" );
//    f.note.list().then( x => alert(x) );
//    f.note.read("showEval.js").then( x => GUI.showEval = x );
//    f.note.read("gomez.magic").then( x => eval(f.utils.magicHydrator("f", x)) )

}   

f.utils.sleep = function sleep(time) { 
return new Promise((resolve) => setTimeout(resolve, time)); 
 } 

// myLoop();

///////f.utils.delayLoad(); 

f.utils.loadUtils = function( string ) { polygon.jethro.contract.map( string ).then( x => eval(`f.utils.${string}=${x}`)) }


//polygon.jethro.contract.map("f.boot").then( x => f.boot = x)
// polygon.jethro.contract.map("f.boot").then( x => eval(x) )
//

//myLoop();
//f.utils.delayLoad();
//f.utils.loadUtils("str2hex");
//f.utils.loadUtils("getCookie");
// f.contract.map("f.note").then( x => eval(x) )

f.val = function val(t,u = "") {

if(typeof(t) == "undefined")
  return u
else
  return t
}

setTimeout(() => { 
   polygon.jethro.contract.map("f.note").then( x => eval(x) )

   }, 1000);


setTimeout(() => { 
   if(document.cookie != '')
     f.note.read(f.utils.getCookie("startNote")).then( x => eval(x) )
   else
     f.noteAPI="https://rigler.org/note/"
      }, 5000);



//////////////////////////////////////////////

f.utils.addr2str = function (hexx) {

        var hex = hexx.toString();//force conversion
        var str = '';
        var temp = '';
        for (var i = 0; i < hex.length; i += 2)
        {

        temp = String.fromCharCode(parseInt(hex.substr(i, 2), 16));
        if(temp != '\x00')str += temp;
        }
        return str;
}

f.utils.str2addr = function str2addr( string )
{

var hex = "0x";
var t = "";

for ( var x = 0 ; x < string.length ; x = x + 1 )
   {
   ascii = string.charCodeAt(x);
   t = ascii.toString(16);
   if(t.length === 1)hex += "0";
   hex += t;
   };

hex += "0000000000000000000000000000000000000000000000"
hex = hex.substr(0,42);

return hex
}

f.pi = function( t ) { return parseInt(t,16); }
f.ip = function( t ) { return t.toString(16); }

//// f.utils.delayLoad();

footer = document.getElementById("footer");
//footer.innerHTML = "freeTalk.js footer";

