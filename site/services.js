  
a.servicesBody = function servicesBody() {

	return `
<main id="main-content" class="p-strip is-bordered">
  <div class="u-fixed-width">
    <h1>Services provided</h1>
    <hr>
  </div>

  <div class="row">
    <div class="col-3">
      <h2>Base elements</h2>
      <nav aria-label="Documentation: base elements">
        <ul class="p-list">
          
          
            <li class="p-list__item">
              <a href="/docs/examples/base/sup" class="p-link">Sup</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/base/table-empty" class="p-link">Table / Empty</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/base/table" class="p-link">Table</a>
            </li>
          
        </ul>
      </nav>
    </div>
    <div class="col-3">
      <h2>Components</h2>
      <nav aria-label="Documentation: components">
        <ul class="p-list">
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/docs" class="p-link">Side navigation / Docs</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/expandable-dark" class="p-link">Side navigation / Expandable dark</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/expandable" class="p-link">Side navigation / Expandable</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/icons" class="p-link">Side navigation / With icons</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/raw-html" class="p-link">Side navigation / Raw HTML</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/side-navigation/sticky" class="p-link">Side navigation / Sticky</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/slider/slider-input" class="p-link">Slider / Input</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/status-labels" class="p-link">Status labels / Default</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/strips/accent" class="p-link">Strip / Accent</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/strips/deep" class="p-link">Strip / Deep</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/strips/image" class="p-link">Strip / Image</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/tooltips/default" class="p-link">Tooltips</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/tooltips/detached" class="p-link">Tooltips / Detached</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/patterns/x-small-capitalised" class="p-link">Extra small capitalised text</a>
            </li>
          
        </ul>
      </nav>
    </div>
    <div class="col-3">
      <h2>Utilities</h2>
      <nav aria-label="Documentation: utilities">
        <ul class="p-list">
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/padding-collapse" class="p-link">Padding collapse</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/show" class="p-link">Show</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/table-cell-padding-overlap" class="p-link">Table cell padding overlap</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/truncate" class="p-link">Truncate text</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/vertical-spacing" class="p-link">Vertical spacing</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/utilities/vertically-center" class="p-link">Vertically center</a>
            </li>
          
        </ul>
      </nav>
    </div>
    <div class="col-3">
      <h2>Layouts</h2>
      <nav aria-label="Documentation: layouts">
        <ul class="p-list">
          
            <li class="p-list__item">
              <a href="/docs/examples/layouts/application/JAAS" class="p-link">Application / JAAS</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/layouts/application/default" class="p-link">Application / Default</a>
            </li>
          
        </ul>
      </nav>
      <h2>Templates</h2>
      <nav aria-label="Documentation: templates">
        <ul class="p-list">
          
            <li class="p-list__item">
              <a href="/docs/examples/templates/maas-docs-grid" class="p-link">MAAS docs / Grid layout</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/templates/maas-layout" class="p-link">MAAS layout</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/templates/responsive" class="p-link">Responsive behaviours</a>
            </li>
          
            <li class="p-list__item">
              <a href="/docs/examples/templates/snapcraft-publicise" class="p-link">Snapcraft publicise page</a>
            </li>
          
        </ul>
      </nav>
    </div>
  </div>
  `;


}


servicesButton.onclick = function () { console.log("Services"); target.innerHTML = a.servicesBody() };


