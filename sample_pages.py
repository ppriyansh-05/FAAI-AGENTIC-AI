BROKEN_STORE_PAGE = '''<!doctype html>
<html>
<head><style>.offer { color: #777; background-color: #fff; }</style></head>
<body>
  <main>
    <h1>Campus Corner Store</h1>
    <img src="coffee-machine.jpg">
    <p class="offer" style="color: #777; background-color: #fff">Students save 10% today.</p>
    <form><input id="email" name="email" type="email" placeholder="Your email"><button>Join offers</button></form>
  </main>
</body>
</html>'''

IMPROVED_STORE_PAGE = '''<!doctype html>
<html lang="en">
<head><title>Campus Corner Store | Student offers</title></head>
<body>
  <main>
    <h1>Campus Corner Store</h1>
    <img src="coffee-machine.jpg" alt="Silver coffee machine dispensing a cappuccino">
    <p style="color: #1f2937; background-color: #ffffff">Students save 10% today.</p>
    <form><label for="email">Email address</label><input id="email" name="email" type="email"><button>Join offers</button></form>
  </main>
</body>
</html>'''
