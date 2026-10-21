
var http = require('http');
var url = require('url');

// Constants
const PORT = 8081;

// App
//const app = express();
http.createServer(function (req, res) { 
  res.writeHeader(200, {'Content-Type': 'text/html'});
  var q = url.parse(req.url, true).query;
  res.end(q.x);
}).listen(PORT);

