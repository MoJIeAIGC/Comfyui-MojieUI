from django.urls import path
from .views import ExampleListView, TemplateListView, TagListView, ExampleCreateView,TemplateCreateView,ExampleSoftDeleteView,realTagListView,ExampleUpdateView,TemplateUpdateView,templateSoftDeleteView\
    ,like_template,FavoriteTemplateView,UserFavoriteTemplateListView,TemplateDetailView,TagCreateView,TagUpdateView,realTagCreateView,realTagUpdateView,TemplateuserView\
   ,webTemplateListView,tagSoftDeleteView,realtagSoftDeleteView,RealtagByTagView,LinkExampleByRealtagView,like_example,PublicTemplateListView

urlpatterns = [
    path('examples/', ExampleListView.as_view(), name='example-list'),
    path('templates/', TemplateListView.as_view(), name='template-list'),
    path('templates_pub/', PublicTemplateListView.as_view(), name='template-list'),
    path('tempweb/', webTemplateListView.as_view(), name='template-list'),
    path('tempinfo/', TemplateDetailView.as_view(), name='template-list'),
    path('category/', TagListView.as_view(), name='template-list'),
    path('tag/', realTagListView.as_view(), name='template-list'),
    path('addExam/', ExampleCreateView.as_view(), name='template-list'),
    path('good/', like_template.as_view(), name='template-list'),
    path('favor/', FavoriteTemplateView.as_view(), name='template-list'),
    path('goodexam/', like_example.as_view(), name='template-list'),
    path('myfavor/', UserFavoriteTemplateListView.as_view(), name='template-list'),
    path('addTemp/', TemplateCreateView.as_view(), name='template-list'),
    path('example/<int:pk>/', ExampleSoftDeleteView.as_view(), name='example-soft-delete'),
    path('template/<int:pk>/', templateSoftDeleteView.as_view(), name='example-soft-delete'),
    path('example/<int:pk>/update/', ExampleUpdateView.as_view(), name='example-soft-delete'),
    path('template/<int:pk>/update/', TemplateUpdateView.as_view(), name='example-soft-delete'),    

    path('addtag/', TagCreateView.as_view(), name='template-list'),
    path('tag/<int:pk>/update/', TagUpdateView.as_view(), name='example-soft-delete'),


    path('addrealtag/', realTagCreateView.as_view(), name='template-list'),
    path('realtag/<int:pk>/update/', realTagUpdateView.as_view(), name='example-soft-delete'),

    path('usertotemp/', TemplateuserView.as_view(), name='example-soft-delete'),

    path('delrealtag/<int:pk>/', realtagSoftDeleteView.as_view(), name='template-list'),
    path('deltag/<int:pk>/', tagSoftDeleteView.as_view(), name='template-list'),

    
    path('getsmall/', RealtagByTagView.as_view(), name='example-soft-delete'),
    path('aaa/', LinkExampleByRealtagView.as_view(), name='example-soft-delete'),
]