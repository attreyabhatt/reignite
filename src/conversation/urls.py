from django.urls import include, path
from conversation.views import conversation_home,ajax_reply,conversation_detail,ocr_screenshot,delete_conversation, log_copy, conversion_event

urlpatterns = [
    path('', conversation_home, name='conversation_home'),
    path('ajax-reply/', ajax_reply, name='ajax_reply'),
    path('detail/<int:pk>/', conversation_detail, name='conversation_detail'), 
    path('ocr-screenshot/', ocr_screenshot, name='ocr_screenshot'),
    path('delete/', delete_conversation, name='delete_conversation'),
    path('copy/', log_copy, name='log_copy'),
    path('conversion-event/', conversion_event, name='web_conversion_event'),

]
