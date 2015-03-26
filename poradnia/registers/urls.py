from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.AdviceList.as_view(), name='list'),
    url(r'^new/$', views.AdviceCreate.as_view(), name="create"),
    url(r'^(?P<pk>\d+)$', views.AdviceDetail.as_view(), name="detail"),
    url(r'^(?P<pk>\d+)/edit$', views.AdviceUpdate.as_view(), name="update"),
    url(r'^(?P<pk>\d+)/delete$', views.AdviceDelete.as_view(), name="delete"),
)
