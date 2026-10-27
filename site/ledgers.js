a.ledgerDisplayBody = function displayBody() {
	return `
<div id="main-content" class="p-strip--suru-topped">
  <div class="row">
    <div class="col-12">
      <h1 class="u-no-margin--bottom">Ledger support</h1>
    </div>
  </div>
</div>

<div class="u-fixed-width">
  <hr class="u-no-margin--bottom">
</div>

<div class="p-strip u-no-padding--bottom">
  <div class="row">
    <div class="col-8">
      <p class="p-heading--4">The value of blockchain is in trusted records. Trust is built by consensus. Traditionally new customers and partners could only guess at the scope and scale of what you could offer. Now it is possible for the world to see deeply into businesses without any private customer data being shared. But the network of trust is bigger than just business. Contact us to learn how we are revolutionizing healthcare, law, lending, and even free speech. No matter what the endeavor, ledger technology cuts out the friction, removes the middle-man, creates records that can not be changed or deleted. Our software and configuration services transform your data into <b>next-level</b> low-friction assets that provide what they advertise. This is your 100% gaurantee, backed by your network partners.  </p>
    </div>
  </div>
</div>
<div class="p-strip is-shallow">
  <div class="row">
    <div class="col-8">
      <h2>Public and private ledgers</h2>
      <ul class="p-list">
        <li class="p-list__item is-ticked">Private ledgers for business networks. </li>
        <li class="p-list__item is-ticked">Public ledgers for the world to see.</li>
        <li class="p-list__item is-ticked">Bring-your-own-identity with Metamask.</li>
      </ul>
    </div>
  </div>
  <div class="row">
    <div class="col-8">
      <h2>Supported ledgers</h2>
      <p>We either build or write to the following blockchain ledgers.</p>
      <ul class="p-list is-split">
        <li class="p-list__item">
          <div class="p-heading-icon--small">
            <div class="p-heading-icon__header">
              <img style="width:100px"  src="branded-icons/Quorum_Logo_Blue_New.svg" alt="" />
              <p class="p-heading-icon__title"></p>
            </div>
          </div>
        </li>
        <li class="p-list__item">
          <div class="p-heading-icon--small">
            <div>
              <img style="width:100px" src="branded-icons/bitcoin.svg" class="p-heading-icon__img" alt="" />
              <p class="p-heading-icon__title"></p>
            </div>
          </div>
        </li>
        <li class="p-list__item">
          <div class="p-heading-icon--small">
            <div class="p-heading-icon__header">
              <img style="width:100px" src="branded-icons/polygon.svg" class="p-heading-icon__img" alt="" />
              <p class="p-heading-icon__title"></p>
            </div>
          </div>
        </li>
        <li class="p-list__item">
          <div class="p-heading-icon--small">
            <div class="p-heading-icon__header">
              <img src="branded-icons/Ethereum-ETH-icon.png" class="p-heading-icon__img" alt="" />
              <p class="p-heading-icon__title">Ethereum</p>
            </div>
          </div>
        </li>
        <li class="p-list__item">
          <div class="p-heading-icon--small">
            <div class="p-heading-icon__header">
              <img style="background-color:blue;width:140px" src="branded-icons/digibyte.svg" class="p-heading-icon__img" alt="" />
              <p class="p-heading-icon__title"></p>
            </div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</div>
`;

}

// target.innerHTML = displayBody();
//
faqButton.onclick = function () { console.log("FAQ"); target.innerHTML = a.ledgerDisplayBody() };


