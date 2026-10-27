a.docsBody = function docsBody() {
	return `
    <div class="p-strip is-shallow">
    <div class="row">
      <aside class="col-3">
        <nav class="p-side-navigation" id="side-navigation-drawer" aria-label="Side">
          <a href="#side-navigation-drawer" class="p-side-navigation__toggle js-drawer-toggle" aria-controls="side-navigation-drawer">
            Toggle side navigation
          </a>

          <div class="p-side-navigation__overlay js-drawer-toggle" aria-controls="side-navigation-drawer"></div>

          <div class="p-side-navigation__drawer">
            <div class="p-side-navigation__drawer-header">
              <a href="#" class="p-side-navigation__toggle--in-drawer js-drawer-toggle" aria-controls="side-navigation-drawer">
                Toggle side navigation
              </a>
            </div>

            

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Welcome</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs" aria-current="page">
                    Get started
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/building-vanilla" >
                    Building with Vanilla
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/customising-vanilla" >
                    Customising Vanilla
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/whats-new" >
                    What’s new in 3.7.1
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/migration-guide-to-v3" >
                    Migrating to v3.0
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Base elements</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/code" >
                    Code
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/forms" >
                    Forms
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/reset" >
                    Reset
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/separators" >
                    Separators
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/tables" >
                    Tables
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/base/typography" >
                    Typography
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Components</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/accordion" >
                    Accordion
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/badge" >
                    Badge
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/breadcrumbs" >
                    Breadcrumbs
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/buttons" >
                    Buttons
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/card" >
                    Cards
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/chip" >
                    Chips
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/contextual-menu" >
                    Contextual menu
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/divider" >
                    Divider
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/empty-state" >
                    Empty state
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/grid" >
                    Grid
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/heading-icon" >
                    Heading icon
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/icons" >
                    Icons
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/images" >
                    Images
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/links" >
                    Links
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/list-tree" >
                    List tree
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/lists" >
                    Lists
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/logo-section" >
                    Logo section
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/matrix" >
                    Matrix
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/media-object" >
                    Media object
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/modal" >
                    Modal
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/muted-heading" >
                    Muted heading
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/navigation" >
                    Navigation
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/notification" >
                    Notifications
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/pagination" >
                    Pagination
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/pull-quote" >
                    Quotes
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/search-and-filter" >
                    Search and filter
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/search-box" >
                    Search box
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/segmented-control" >
                    Segmented control
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/slider" >
                    Slider
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/status-labels" >
                    Status labels
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/strip" >
                    Strip
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/switch" >
                    Switch
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/table-of-contents" >
                    Table of contents
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/tabs" >
                    Tabs
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/patterns/tooltips" >
                    Tooltips
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Utilities</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/align" >
                    Align
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/baseline-grid" >
                    Baseline grid
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/clearfix" >
                    Clearfix
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/embedded-media" >
                    Embedded media
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/equal-height" >
                    Equal height
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/floats" >
                    Floats
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/font-metrics" >
                    Font metrics
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/functions" >
                    Functions
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/hide" >
                    Hide
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/image-position" >
                    Image position
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/margin-collapse" >
                    Margin collapse
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/no-print" >
                    No print
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/off-screen" >
                    Off-screen
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/padding-collapse" >
                    Padding collapse
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/table-cell-padding-overlap" >
                    Table cell padding overlap
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/truncate" >
                    Truncation
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/show" >
                    Show
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/vertical-spacing" >
                    Vertical spacing
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/utilities/vertically-center" >
                    Vertically center
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Layouts</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/layouts/application" >
                    Application
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/layouts/documentation" >
                    Documentation
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/layouts/fluid-breakout" >
                    Fluid breakout
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/layouts/sticky-footer" >
                    Sticky footer
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Settings</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/animation-settings" >
                    Animations
                    
                      <span class="p-side-navigation__status">
                        <span class="p-status-label--information">
                          Updated
                        </span>
                      </span>
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/assets-settings" >
                    Assets
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/breakpoint-settings" >
                    Breakpoints
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/color-settings" >
                    Color
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/font-settings" >
                    Font
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/layout-settings" >
                    Layout
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/placeholder-settings" >
                    Placeholders
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/spacing-settings" >
                    Spacing
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/settings/table-layout" >
                    Table layout
                    
                  </a>
                </li>
            </ul>

            <ul class="p-side-navigation__list">
              <li class="p-side-navigation__item--title"><span class="p-side-navigation__text">Resources</span></li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="/docs/examples" >
                    Component examples
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="https://github.com/canonical/vanilla-framework/releases/latest" >
                    Release notes for 3.7.1
                    
                  </a>
                </li>
              <li class="p-side-navigation__item">
                  <a class="p-side-navigation__link" href="https://assets.ubuntu.com/latest-redirects/vanilla-framework.sketch" >
                    Download Sketch UI Kit
                    
                  </a>
                </li>
            </ul>

          </div>
        </nav>

      </aside>

      <main class="col-9" id="main-content">
        
<h1>Private Blockchains are Poised to revolutionize every vertical.</h1>

<hr>

<p>By now, we have all heard about how Bitcoin has revolutionized international commerce. We have also heard about how Ethereum has been central to creating new (and sometimes strange) way of exchanging digital assets. But did you know that companies like yours are already exploring private blockchain ledger? 

<p>Developed at <a href=https://consensys.net/quorum/>JPMorgan</a> the Quorum Byzantine Fault Tolerant (QBFT) private Ethereum Ledger has become to industry standard for early adopters across all sectors.</p>

<p>For example, the Synaptic Health Alliance includes: Humana, MultiPlan, Quest, and United Healthcare.</p>

<p>Contact us today to learn how to tokenize, credential, and secure your valuable healthcare data.</p>

<a href=https://www.synaptichealthalliance.com/hubfs/Downloadables/Synaptic_Health_Alliance_Blockchain_White_Paper_2022.pdf> Download the Synaptic HealthAlliance Whitepaper</a>

      </main>

    </div>
    </div>`;
}

console.log("docs...")

docsButton.onclick = function () { console.log("About"); target.innerHTML = a.docsBody() };

