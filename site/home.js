function loadBody () {

 return `<script defer src="/lib/buttons.js"></script>

<div id="main-content" class="p-strip--suru is-deep">
  <div class="row">
    <div class="col-12">
      <h1 id="pageTitle">pageTitle</h1>
      <p id="pageBlurb">pageBlurb</p>
      <ul class="p-inline-list u-no-margin--bottom">
        <li class="p-inline-list__item">
          <a id="contactUs" class="p-button--positive u-no-margin--bottom">contactUs</a>
        </li>
        <li class="p-inline-list__item">
          <a id="contactZoom" class="p-button u-no-margin--bottom">contactZoom</a>
        </li>
      </ul>
    </div>
  </div>
</div>

<div class="p-strip is-bordered is-deep">
  <div class="row" id="bulletRow">
    <div class="col-4">
      <div class="p-heading-icon">
        <div class="p-heading-icon__header is-stacked">
          
<div class="lazyload" data-noscript>
    <img
      alt=""
      width="96"
      height="96"
    />
</div>

          <h2 class="p-heading-icon__title">bulletRow[0]</h2>
        </div>
        <p>bulletRow[0]</p>
      </div>
    </div>

    <div class="col-4">
      <div class="p-heading-icon">
        <div class="p-heading-icon__header is-stacked">


    <div class="lazyload" data-noscript>
      <img
       alt=""
       width="96"
       height="96"
      />
    </div>
          <h2 class="p-heading-icon__title">bulletRow[1]</h2>
        </div>
        <p>bulletRow[1]</p>

      </div>
    </div>
    <div class="col-4">
      <div class="p-heading-icon">
        <div class="p-heading-icon__header is-stacked">
         

<div class="lazyload" data-noscript>
    <img
      alt=""
      width="96"
      height="96"
    />
</div>

          <h2 class="p-heading-icon__title">bulletRow[2]</h2>
        </div>
        <p>bulletRow[2]</p>
      </div>
    </div>
  </div>
</div>

<div id="quickStart" class="p-strip is-bordered is-deep">
  <div class="row">
    <div class="col-12">
      <h2>quickStart</h2>
    </div>
  </div>
  <div class="row">
    <div class="col-6">
      <p>quickStart</p>
      </div>
      <h2>quickStart</h2>
  </div>
</div>
`;
}

target.innerHTML = loadBody();

fetchHome = function(toFetch) {

fetch(toFetch).then( x => x.json() ).then( x => {
    pageTitle.innerHTML = x.pageTitle;
    pageBlurb.innerHTML = x.pageBlurb;
    contactUs.innerHTML = x.contactUs;
    contactZoom.innerHTML = x.contactZoom;
      a.script = x;
        console.log(x)

    for(y = 0; y < 3; y++)
	{
		console.log(y)
	thisRow = bulletRow.children[y].children[0]
	thisRow.children[0].children[0].children[0].src = '/icon/' + a.script.bulletRow[y].icon
	thisRow.children[0].children[1].innerHTML = a.script.bulletRow[y].header 
	thisRow.children[1].innerHTML = a.script.bulletRow[y].body 
	}

   quickStart.children[0].children[0].innerHTML = "<h2>" + a.script.quickStart.header + "</h2>"
   quickStart.children[1].children[0].innerHTML = a.script.quickStart.body; 
   quickStart.children[1].children[1].innerHTML = a.script.quickStart.cta;


})

}

fetchHome("home.json?14343")

contactUs.onclick = function () { console.log("contactUs") ; setLocationHref("#footerContact") };

