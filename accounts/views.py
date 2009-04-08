from django.shortcuts import render_to_response

def profile(request):
    user = request.user
    return render_to_response('accounts/profile.html', {
        'user': user,
    })  