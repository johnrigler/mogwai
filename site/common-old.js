document.title = 'Secret_Beach_Solutions'

// is-selected

var setMainMenu = `
<ul class="p-navigation__items" id="mainMenu">
        <li><a class="p-navigation__link" id="ledgers">Ledgers</a></li>
        <li><a class="p-navigation__link" id="about">About Us</a></li>
      </ul>`;

var setFooter = `
<footer class="p-strip--light">
  <div class="row p-content__row">
    <div class="col-12">
      <nav aria-label="Footer">
        <ul class="p-inline-list--middot u-no-margin--bottom">
          <li class="p-inline-list__item">
            <div id="footerContact">
	    <h3>
	    <pre>

	    John Rigler <a href=https://linkedin.com/in/jrigler><img src="/icon/linkedin.svg"></a>
	    Collective Ledgers, LLC
	    john@protonmail.com
	    682-666-0614
	    </pre>
	    </h3>
	    </div>
          </li>
          <li class="p-inline-list__item">
            &copy; 2025 Secret Beach Solutions 
          </li>
        </ul>
        <span class="u-off-screen">
          <a href="#">Go to the top of the page</a>
        </span>
      </nav>
    </div>
  </div>
</footer>
`;

function setLocationHref ( page ) {
	console.log(page)
	location.href = "https://secretbeachsolutions.com/cl/" + page;
}

function loadPage ( page ) {

	alert(page);

}

mainMenu = document.getElementById("mainMenu");
mainMenu.innerHTML = setMainMenu;

var page = window.location.href.substr(50);

var homeMenu = document.getElementById("homeButton");
var homeImage = document.getElementById("homeImage");
var blockchainMenu = document.getElementById("blockchain");
var target = document.getElementById("target");
var footer = document.getElementById("addFooter");

footer.innerHTML = setFooter;

homeMenu.onclick = function () { console.log("click") ;  setLocationHref("") }; // was vf/
homeImage.onclick = function () { setLocationHref("") }; // was vf/
//blockchainMenu.onclick = function () { location.href = "https://secretbeachsolutions.com/vanillaframework/" };
// example.onclick = function () { setLocationHref("https://secretbeachsolutions.com/vanillaframework/examples/") } ;
//services.onclick = function () { setLocationHref("vanillaframework/services/") };
about.onclick = function () { setLocationHref("about/") }; // was vf/about/
ledgers.onclick = function () { setLocationHref("ledgers/") };

if(page == '')page = 'index.html';

