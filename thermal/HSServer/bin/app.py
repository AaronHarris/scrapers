import web

urls = (
  '/', 'Index'
)

app = web.application(urls, globals())

render = web.template.render('templates/')

class Index(object):
    def GET(self):
        return render.index(greesting = "Hello World")

if __name__ == "__main__":
    app.run()