# Mogwai

## Dated concept notes

- [2026-09-11 — User-Controlled Interactive Frame](README-2026-09-11.md)

The dated notes preserve the evolution of Mogwai's architecture. The 2026-09-11 note defines Mogwai as the interactive frame for user-controlled media resolution, including YouTube/IPFS decomposition and its relationship to Dark Star, CertLedger, and Chisel.

---

********************************************************
ETHDENVER 2025 Update!!!!!!!!!!

 https://www.google.com/search?q=walmart+thermal+printer&oq=walmart+thermal+printer&gs_lcrp=EgZjaHJvbWUyBggAEEUYOdIBCjI0MTM5ajBqMTWoAgCwAgA&sourceid=chrome&ie=UTF-8#pvs=0&oshopproduct=gid:14749531635230207023,mid:576462813627866715,oid:9898510862179736551,iid:17543297358764239666,rds:UENfMTQ3NDk1MzE2MzUyMzAyMDcwMjN8UFJPRF9QQ18xNDc0OTUzMTYzNTIzMDIwNzAyMw%3D%3D,pvt:hg,pvo:3,laoid:9898510862179736551&oshop=apv



*********************************************************


The point of this project is to present working demonstrations of "Web3". The term means different things to different people, but I want to share what
it means to me. Then people can better judge for themselves. I will probably create many sub-projects that are all pretty simple. When I first imagined
this project, I did some work with the Godot game developement API. It seems as if academia hasn't quite embraced Godot as a game-development solution, 
but I find it useful because it is open-source. Almost any crypto/blockchain related project built with a more commercial engine would potential run into issues as things such as NFTs seem to be banned.

I am a data hacker. If you want to understand more about what this means, then you might take a look at Paul Graham's book/site:

https://paulgraham.com/hp.html

If you are unfamiliar with Paul Graham, he is sometimes considered to be the father of Web2. He pioneered the idea that stuff could be done on a Web page, many
years before Google was a thing. He created a company called Viaweb which was eventually integrated into the Yahoo store creation toolkit. He then went on
to found the highly influencial tech incubator: Y-Combinator.

Anyhow, to me, being a "hacker" has nothing to do with being some sort of cyber-security black hat. Rather, it is about engineering unique new ideas into software.
It is about revealing things which are only obvious after they are explained. One of my biggest revelations is that we are far too dependent on building Javascript
websites using NodeJS running on a server which relies on React/Vue/NextJS, etc. frameworks. These solutions seem necessary, but they are not. Without them, greater 
decentralization is possible. 

Often Web2 sites are organized with a graphical front-end rendered by a React server and a backend that is comprised of a python, rust, or goLang API which runs as
a daemon and listens to some port such as 3000. The API reads and writes from a database. One of the first purposes of the database is to house an identity
system with encryptoed passwords, email password reset functionality, and other general housekeeping. The user's id can be blocked or deleted if necessary.

In Web3, the user controls their own identity, so a large part of this server functionality is not necessary. This is why metamask and other similar tools are
so important. To further understand why this identity system is so special, you could read about Zooko's
Trilemma:

https://en.wikipedia.org/wiki/Zooko%27s_triangle

Basically, Web3/Crypto identities are decentalized and secure, but never human-readable. An example of this 
might be a bitcoin address. A bitcoin address is a series of numbers and letters (technically in Base-58) 
which is derrived from a secret key. The end-user is the only person that knows the secret key. Cryptography
is used in order to transform into a hash. This is the non-readable address.

So without the need for a Nodejs server, and without the need for server-based identity, it becomes 
possible to have website that aren't quite owned by anyone. They can be hosted locally or using the 
Interplanetary Filesystem (IPFS). 

I have created examples of all of this that I will begin to add. I know this is all alot of stuff, but it is 
totally 100% something that you guys can figure out. Web3 is very new and figuing out how it works only
seems complicated until its secrets are revealed.

Oh, and here is an example of Web3. It may take a while to load:

https://ipfs.io/ipfs/QmTCpNfG8tH9yEibWHfb5T9vZej5joSn6zMYR8nvQZJSJx/gomez.html

It is possible to write messages in raw HTML onto this "forever wall" by using Metamask and the Polygon
crypto.  I don't believe that things written onto this can ever be deleted or censored. This leads to
a much bigger conversation about gatekeeping, morality, and even the future of social media.
