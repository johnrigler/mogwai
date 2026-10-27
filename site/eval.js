m.utils.eval = function() {

addExample = function addExample() {

toEval.innerHTML = `m.utils.evalFile("eval/oldPinner.js")
output.innerHTML = m.oldPinner.address
// Run twice to get to work`

}

middle.innerHTML=`
<textarea id="toEval" name="toEval" rows="8" cols="50">
alert("update toEval.innerHTML to change this remotely.")
</textarea>
<hr>
<button onclick="eval(toEval.value)">Run</button>
<button onclick="toEval.innerHTML=''">Clear</button>` 
+
'<button onclick="addExample()">Example</button><div id=output></div>'
} 

addExamplex = function() { console.log("x") }
m.utils.eval()
