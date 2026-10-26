from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_safe


# App signing certificate from Play Console, not the local upload certificate.
PLAY_APP_SIGNING_SHA256 = (
    "7C:CF:42:5B:FD:40:FC:15:10:64:A1:4B:09:F8:FA:55:"
    "DE:3F:8D:D8:78:C0:60:81:67:F8:C1:FF:0A:89:F5:40"
)


@require_safe
@cache_control(public=True, max_age=3600)
def android_asset_links(request):
    return JsonResponse([
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.tryagaintext.flirtfix",
                "sha256_cert_fingerprints": [PLAY_APP_SIGNING_SHA256],
            },
        },
    ], safe=False)
