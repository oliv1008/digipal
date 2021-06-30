from django import forms
from digipal.views.content_type.search_content_type import SearchContentType, get_form_field_from_queryset
from digipal.models import Image, Text
from digipal_text.models import TextContent, TextContentXML
from digipal_project.models import Bonhum_Source, Bonhum_TextSource
from django.db.models import Q
import re

class FilterSources(forms.Form):
    source = get_form_field_from_queryset(Bonhum_Source.objects.values_list('title', flat=True).order_by('title').distinct(), 'Source')
    type = get_form_field_from_queryset(Bonhum_Source.objects.values_list('type__name', flat=True).order_by('type__name').distinct(), 'Type', aid='type')
    author = get_form_field_from_queryset(Bonhum_Source.objects.values_list('authors__name', flat=True).order_by('authors__name').distinct(), 'Author', aid='author')

class SearchSources(SearchContentType):

    def get_fields_info(self):
        ''' See SearchContentType.get_fields_info() for a description of the field structure '''
        ret = super(SearchSources, self).get_fields_info()
        return ret

    def get_sort_fields(self):
        ''' returns a list of django field names necessary to sort the results '''
        return ['title']

    def set_record_view_context(self, context, request):
        super(SearchSources, self).set_record_view_context(context, request)
        source = Bonhum_Source.objects.get(id=context['id'])
        context['source'] = source

        from bs4 import BeautifulSoup
        text_content_xmls = TextContentXML.objects.filter(
                                text_content__text__id__in=source.texts.values_list('id')
                            )
        texts = []
        for tcx in text_content_xmls:
            references_in_db = Bonhum_TextSource.objects.filter(source__id=source.id).filter(text__id=tcx.text_content.text.id).values_list('canonical_reference', flat=True)
            soup = BeautifulSoup(tcx.content, 'lxml')
            quotes = soup.find_all('span', attrs={ 'data-dpt': 'quote',
                                                   'data-dpt-corresp': re.compile(ur'.*?#'
                                                   + str(source.id) + ur'\b.*?')})
            annotations = {}
            for quote in quotes:
                n = str(quote.attrs.get('data-dpt-n'))
                content = quote.get_text()
                references_in_tcx = re.findall(source.reference + ur' \((.*?)\)|' + source.reference, n)[0]
                if len(references_in_tcx) == 0:
                    annotations.setdefault('No reference', []).append(content)
                else:
                    for reference in references_in_tcx.split(' ; '):
                        annotations.setdefault(reference, []).append(content)
            for reference in references_in_db:
                if len(reference) > 0 and reference not in annotations:
                    annotations[reference] = []
            texts.append({
                'text_content_xml': tcx,
                'annotations': annotations
            })

        context['texts'] = texts

    def get_model(self):
        return Bonhum_Source

    def get_form(self, request=None):
        initials = None
        if request:
            initials = request.GET
        return FilterSources(initials)

    @property
    def key(self):
        return 'sources'

    @property
    def label(self):
        return 'Sources'

    @property
    def label_singular(self):
        return 'Source'

    def _build_queryset_django(self, request, term):
        type = self.key
        query_characters = Bonhum_StoryCharacter.objects.filter(
                    Q(title__icontains=term) | \
                    Q(type__name__icontains=term) | \
                    Q(authors__name__icontains=term))

        title = request.GET.get('title', '')
        type = request.GET.get('type', '')
        author = request.GET.get('author', '')

        if title:
            query_sources = query_sources.filter(title=title)
        if type:
            query_sources = query_sources.filter(type__name=type)
        if author:
            query_sources = query_sources.filter(authors__name=author)

        self._queryset = query_sources.distinct().order_by('title')

        return self._queryset
