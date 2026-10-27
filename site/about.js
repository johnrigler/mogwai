a.aboutBody = function aboutBody() {
	return `
<div id="main-content" class="p-strip--suru-topped">
  <div class="row">
    <div class="col-12">
      <h1>About Us</h1>
      <p>Secret Beach Solutions is a Blockchain Infrastructure and Development Company. We meet your business where-ever you are on the technology spectrum. By building ledger technology directly onto your servers, we allow you to create a new form of Digital NFT assets. We are a cutting-edge greenfield firm. Our customers are normal businesses who are ready to explore the next iteration of blockchain technology. We are exciting that you are coming on this journey with us.</p>
    </div>
  </div>
</div>

<div class="u-fixed-width">
  <hr class="u-no-margin--bottom">
</div>

`;

}

console.log("About....")

aboutButton.onclick = function () { console.log("About"); target.innerHTML = a.aboutBody() };

