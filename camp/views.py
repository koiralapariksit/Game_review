from django.shortcuts import render

def home(request):
    return render(request, 'camp/home.html')

def media(request):
    return render(request, 'camp/media.html')


# def latest_match_highlight(request):
#     return HttpResponse("<h2>Latest Match Review Highlight</h2><p>Coming soon...</p>")

# def countdown_to_next_match(request):
#     return HttpResponse("<h2>Countdown to Next Match</h2><p>Timer here...</p>")

# def social_feed(request):
#     return HttpResponse("<h2>Live Social Media Feed</h2><p>Embedded tweets, posts, etc.</p>")
