from webbrowser import get
from django import forms
from digipal.views.content_type.search_content_type import SearchContentType, \
get_form_field_from_queryset
from digipal.models import Image, MediaPermission
from django.forms.models import model_to_dict
from digipal_text.models import TextContentXML
from digipal_project.models import Bonhum_StoryCharacter, Bonhum_StoryPlace
from django.forms.widgets import Select
from django.db.models import Q
from mezzanine.conf import settings
from digipal.utils import is_staff
from collections import OrderedDict
from bs4 import BeautifulSoup
import re
import json
import pdb
import copy

def get_TE_buttons_info(category_id):
    TE_buttons = settings.TEXT_EDITOR_OPTIONS_CUSTOM['buttons']['btnPerson']
    buttons = []
    category = next((category for category in TE_buttons['categories']
                    if category['id'] == category_id), None)
    if category:
        for item in category['items']:
            buttons.append({
                'code': item['attributes']['ana'],
                'label': item['label']
            })
    return buttons

# Types of social relationships
social_types = [
    '#PROS-EV-REL-TY-SOC',
    '#PROS-EV-REL-TY-SOC-TY-PRO',
    '#PROS-EV-REL-TY-SOC-TY-INST',
    '#PROS-EV-REL-TY-SOC-TY-AMOR',
    '#PROS-EV-REL-TY-SOC-TY-AMIC',
    '#PROS-EV-REL-TY-SOC-TY-HOST'
]

# Levels of social relationships
social_levels = {
    '#PROS-EV-REL-TY-SOC-N-AVECI': 'With an inferior',
    '#PROS-EV-REL-TY-SOC-N-AVECS': 'With a superior',
    '#PROS-EV-REL-TY-SOC-N-AVECP': 'With an equal'
}

# Inverses of social relationships levels, to determine the code to use when
# the character is the object of the annotation
# e.g. "A is the superior of B" -> B is the inferior of A
social_levels_inverses = {
    '#PROS-EV-REL-TY-SOC-N-AVECI': '#PROS-EV-REL-TY-SOC-N-AVECS',
    '#PROS-EV-REL-TY-SOC-N-AVECS': '#PROS-EV-REL-TY-SOC-N-AVECI',
    '#PROS-EV-REL-TY-SOC-N-AVECP': '#PROS-EV-REL-TY-SOC-N-AVECP'
}

# Inverses of familial relationships, to determine the code to use when
# the character is the object of the annotation
# e.g. "A is the child of B" -> B is the parent of A
# e.g. "A is the nephew of B" -> if B has 1 as gender, B is the uncle of A;
# if B has 2 as gender, B is the aunt of A (if no gender is given, the default is 1)
familial_inverses = {
    '#PROS-EV-REL-TY-FAM-PAR': '#PROS-EV-REL-TY-FAM-ENF',
    '#PROS-EV-REL-TY-FAM-ENF': '#PROS-EV-REL-TY-FAM-PAR',
    '#PROS-EV-REL-TY-FAM-GRPAR': '#PROS-EV-REL-TY-FAM-PTSENF',
    '#PROS-EV-REL-TY-FAM-PTSENF': '#PROS-EV-REL-TY-FAM-GRPAR',
    '#PROS-EV-REL-TY-FAM-NIEC': { 1: '#PROS-EV-REL-TY-FAM-ONC', 2: '#PROS-EV-REL-TY-FAM-TAN' },
    '#PROS-EV-REL-TY-FAM-NEV': { 1: '#PROS-EV-REL-TY-FAM-ONC', 2: '#PROS-EV-REL-TY-FAM-TAN' },
    '#PROS-EV-REL-TY-FAM-TAN': { 1: '#PROS-EV-REL-TY-FAM-NEV', 2: '#PROS-EV-REL-TY-FAM-NIEC' },
    '#PROS-EV-REL-TY-FAM-ONC': { 1: '#PROS-EV-REL-TY-FAM-NEV', 2: '#PROS-EV-REL-TY-FAM-NIEC' }
}

class FilterCharacters(forms.Form):
    character_type = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('type__name', flat=True).order_by('type__name').distinct(), 'Type', aid='character_type')
    gender = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('gender__name', flat=True).order_by('gender__name').distinct(), 'Gender', aid='gender')
    age = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('age__name', flat=True).order_by('age__name').distinct(), 'Age', aid='age')
    religion = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('religion__name', flat=True).order_by('religion__name').distinct(), 'Religion', aid='religion')
    title = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('titles__name', flat=True).order_by('titles__name').distinct(), 'Title', aid='title')
    origin = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('geographical_origin__name', flat=True).order_by('geographical_origin__name').distinct(), 'Geographical Origin', aid='geographical_origin')
    trait = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('traits__name', flat=True).order_by('traits__name').distinct(), 'Trait', aid='trait')
    occupation = get_form_field_from_queryset(Bonhum_StoryCharacter.objects.values_list('occupations__name', flat=True).order_by('occupations__name').distinct(), 'Occupation', aid='occupation')
    status = forms.ChoiceField(
        choices=[('', 'Status')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_status')],
        widget=Select(attrs={'id': 'status', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Status'}),
        label='', initial='Status', required=False
    )
    psychology = forms.ChoiceField(
        choices=[('', 'Psych. Condition')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_psychology')],
        widget=Select(attrs={'id': 'psychology', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Psych. Condition'}),
        label='', initial='Psych. Condition', required=False
    )
    socio_eco_status = forms.ChoiceField(
        choices=[('', 'Socio-eco. Status')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_socio_economic_status')[0:3]],
        widget=Select(attrs={'id': 'socio_eco_status', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Socio-eco. Status'}),
        label='', initial='Socio-eco. Status', required=False
    )
    socio_eco_level = forms.ChoiceField(
        choices=[('', 'Socio-eco. Level')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_socio_economic_status')[3:6]],
        widget=Select(attrs={'id': 'socio_eco_level', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Socio-eco. Level'}),
        label='', initial='Socio-eco. Level', required=False
    )
    culture = forms.ChoiceField(
        choices=[('', 'Culture')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_culture')],
        widget=Select(attrs={'id': 'culture', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Level of Language'}),
        label='', initial='Culture', required=False
    )
    familial_rel = forms.ChoiceField(
        choices=[('', 'Familial Rel.')] +
                [(button['code'], button['label']) for button in get_TE_buttons_info('person_familial_relationships')[0:5]] +
                [('ONC-TAN', 'Uncle/Aunt'), ('NEV-NIEC', 'Nephew/Niece')] +
                [(button['code'], button['label']) for button in get_TE_buttons_info('person_familial_relationships')[9:12]],
        widget=Select(attrs={'id': 'familial_rel', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Familial Rel.'}),
        label='', initial='Familial Rel.', required=False
    )
    social_rel_type = forms.ChoiceField(
        choices=[('', 'Social Rel. Type')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_social_relationships')[0:6]],
        widget=Select(attrs={'id': 'social_rel_type', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Social Rel. Type'}),
        label='', initial='Social Rel. Type', required=False
    )
    social_rel_level = forms.ChoiceField(
        choices=[('', 'Social Rel. Level')] + [(button['code'], button['label'])
                                               for button in get_TE_buttons_info('person_social_relationships')[6:9]],
        widget=Select(attrs={'id': 'social_rel_level', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Social Rel. Level'}),
        label='', initial='Social Rel. Level', required=False
    )
    linked_place = forms.ChoiceField(
        choices=[('', 'Linked Place')] + [(place.id, place.name) for place in Bonhum_StoryPlace.objects.all()],
        widget=Select(attrs={'id': 'linked_place', 'class': 'chzn-select',
                             'data-placeholder': 'Choose a Place'}),
        label='', initial='Linked Place', required=False
    )

class SearchCharacters(SearchContentType):

    def get_fields_info(self):
        ''' See SearchContentType.get_fields_info() for a description of the field structure '''
        ret = super(SearchCharacters, self).get_fields_info()
        return ret

    def get_sort_fields(self):
        ''' returns a list of django field names necessary to sort the results '''
        return ['name']

    def get_headings(self):
        return [
            {'label': 'Name', 'key': 'name', 'is_sortable': True},
            {'label': 'Type', 'key': 'type', 'is_sortable': True},
            {'label': 'Age', 'key': 'age', 'is_sortable': True},
            {'label': 'Gender', 'key': 'gender', 'is_sortable': True}
        ]

    #Return time marker relative to the total length of the text on annotations to allow data visualization
    def get_temporal_marker(self, soup, span, text_len, tcx):
        #An unique string is used to prevent problems due to tag sharing the same content (ex : a name), it is cleaned after each tag has been temporally marked
        old_tag_string = span.string
        span.string = "UNIQUE_FLAG"
        position = str(soup).find("UNIQUE_FLAG")
        if old_tag_string is not None:
            span.string = old_tag_string
        else:
            print("Erreur, comportement imprevu, probablement erreur dans le texte : " + str(tcx))
            span.string = ""
        return round(float(position)/float(text_len), 2) * 100

    #Return the "characteristics" python dictionnary as a json dictionnary
    #Some keys and values of the python dictionnary are non serializable python objects, the goal of this method is to manually serialize them to create 
    #the json dictionnary
    def get_characteristics_as_json(self, characteristics):
            characteristics_as_json = copy.deepcopy(characteristics)
            for characteristic in characteristics_as_json:
                for code_key, code_value in characteristic['codes'].items():
                    #Initially, the key of characteristics['codes']['annotations'].items is an 'TextContentXML' object, we're only keeping the title of the text 
                    annotations_key_to_string = { k.text_content.text.title : v for k, v in code_value['annotations'].items()}
                    if ("EV-ST" in code_key or "EV-REL" in code_key):
                        for annotations_key_to_string_value in annotations_key_to_string.values():
                            for annotation in annotations_key_to_string_value:
                                if annotation['in_relation_with']:
                                    #Initially, the value of characteristics['codes']['annotations'][Text]['in_relation_with'] is an 'BonhumStoryCharacter' object, we're manually serializing the object to a dictionnary of its value
                                    annotation_value_to_string = [model_to_dict(x) for x in annotation['in_relation_with']]
                                    annotation['in_relation_with'] = annotation_value_to_string
                    if ('PROS-L' in code_key):
                        for annotations_key_to_string_value in annotations_key_to_string.values():
                            for annotation in annotations_key_to_string_value:
                                #Initially, the value of characteristics['codes']['annotations'][Text]['place'] is an 'BonhumStoryPlace' object, we're manually serializing the object to a dictionnary of its value
                                annotation['place'] = model_to_dict(annotation['place'])

                    code_value['annotations'] = annotations_key_to_string
            return json.dumps(characteristics_as_json)

    def set_record_view_context(self, context, request):
        super(SearchCharacters, self).set_record_view_context(context, request)
        character = Bonhum_StoryCharacter.objects.get(id=context['id'])
        context['character'] = character

        graphs = character.get_graphs()
        if not is_staff(request):
            private_images = Image.filter_permissions(
                Image.objects.all(), [MediaPermission.PERM_PRIVATE])
            graphs = graphs.exclude(annotation__image__in=private_images)
        context['graphs'] = graphs

        text_content_xmls = TextContentXML.objects.all() if is_staff(request) else TextContentXML.get_public_only()
        text_content_xmls = text_content_xmls.filter(text_content__text__id__in=character.texts.values_list('id'))
        context['text_content_xmls'] = text_content_xmls

        # We get the buttons used to annotate the texts
        TE_buttons = settings.TEXT_EDITOR_OPTIONS_CUSTOM['buttons']
        # We get the categories of three buttons: person, time and place
        categories = TE_buttons['btnPerson']['categories'] + TE_buttons['btnTime']['categories'] + TE_buttons['btnPlace']['categories']

        # For each category, we get all its items (ana code and label) and add them to our characteristics
        characteristics = []
        for category in categories:
            codes = OrderedDict()
            for item in category['items']:
                if item['id'] != 'btnPersonName':
                    codes.update({
                        item['attributes']['ana']: { 'label': item['label'], 'annotations': {}, 'nb': 0 }
                    })
                else:
                    codes.update({
                        'person_name': { 'label': item['label'], 'annotations': {}, 'nb': 0 }
                    })
            label = category['label']
            if len(label) == 0:
                label = 'Time' if category['items'][0]['tag'] == 'date' else 'Place'
            characteristics.append({
                'label': label,
                'codes': codes,
                'nb': 0
            })

        # For each text_content_xml linked to the character
        for tcx in text_content_xmls.filter(content__isnull=False):
            soup = BeautifulSoup(tcx.content, 'lxml')
            # We get the <rs> annotations in which the character is subject
            # (i.e. when the ref attribute starts with the character id)
            rs_subject_spans = soup.find_all('span', attrs={ 'data-dpt': 'rs',
                                                   'data-dpt-ref': re.compile(ur'^#'
                                                   + str(character.id) + ur'\b.*?') })
            # We get the <rs> annotations in which the character is object
            # (i.e. when the ref attribute includes the character id, but NOT in first position)
            rs_object_spans = soup.find_all('span', attrs={ 'data-dpt': 'rs',
                                                   'data-dpt-ref': re.compile(ur'(?!#'
                                                   + str(character.id) + ur'\b).*?#'
                                                   + str(character.id) + ur'\b.*?') })
            # We get the <persName> annotations in which the ref attribute is the character id
            persname_spans = soup.find_all('span', attrs={ 'data-dpt': 'persName',
                                                   'data-dpt-ref': '#' + str(character.id)})
            # We get the <date> annotations related to the character
            # (i.e. when the ref attribute includes the character id)
            date_spans = soup.find_all('span', attrs={ 'data-dpt': 'date',
                                                   'data-dpt-ref': re.compile(ur'.*?#'
                                                   + str(character.id) + ur'\b.*?') })
            # We get the <placeName> annotations related to the character
            # (i.e. when the ref attribute includes the character id,
            # but NOT in first position, since the first id is the one of the place)
            place_spans = soup.find_all('span', attrs={ 'data-dpt': 'placeName',
                                                   'data-dpt-ref': re.compile(ur'(?!#'
                                                   + str(character.id) + ur'\b).*?#'
                                                   + str(character.id) + ur'\b.*?') })

            text_len = len(tcx.content)

            # For each <persName>, <placeName> and <date> annotation
            spans = persname_spans + place_spans + date_spans
            for span in spans:
                position_percentage = self.get_temporal_marker(soup, span, text_len, tcx)

                url = tcx.get_absolute_url()
                url += '?' if ('?' not in url) else '&'
                url += 'annotation=%s' % span.attrs.get('data-dpt-id')
                tag = span.attrs.get('data-dpt')
                code = span.attrs.get('data-dpt-ana') if tag != 'persName' else 'person_name'
                content = span.get_text()
                data = { 'content': content, 'url': url, 'position_percentage' : position_percentage}
                # If the annotation is <placeName>, we extract the first id
                # in the ref attribute and get the matching place in database
                if tag == 'placeName':
                    ref = span.attrs.get('data-dpt-ref').split(' ')
                    place_id = int(ref.pop(0)[1:])
                    place = Bonhum_StoryPlace.objects.get(id=place_id)
                    data['place'] = place
                # We add the related text segment to our characteristics regarding
                # the code in the ana attribute, with the related place for <placeName>
                for category in characteristics:
                    if code in category['codes'].keys():
                        category['codes'][code]['annotations'].setdefault(tcx, []).append(data)
                        category['codes'][code]['nb'] += 1
                        category['nb'] += 1

            # For each <rs> annotation (with the character as subject or object)
            spans = rs_subject_spans + rs_object_spans
            for span in spans:
                position_percentage = self.get_temporal_marker(soup, span, text_len, tcx)
                
                url = tcx.get_absolute_url()
                url += '?' if ('?' not in url) else '&'
                url += 'annotation=%s' % span.attrs.get('data-dpt-id')
                ana = span.attrs.get('data-dpt-ana')
                ref = span.attrs.get('data-dpt-ref').split(' ')
                content = span.get_text()
                in_relation_with = []
                is_object = False
                if len(ref) > 1:
                    # If ref contains more than one id, we extract all the ids in the
                    # ref attribute that are not the one of the character, and get the
                    # matching characters in database; if the first id is not the one of
                    # the character, it means it is an object in the annotation, not the subject
                    ref = [ int(id[1:]) for id in ref ]
                    if ref[0] != character.id:
                        is_object = True
                    ref = filter(lambda id: id != character.id, ref)
                    in_relation_with = [ Bonhum_StoryCharacter.objects.get(id=id) for id in ref ]
                ana = ana.split(' ')
                # We get the codes related to social relationships levels and types
                ana_levels = [ a for a in ana if a in social_levels.keys() ]
                ana_types = [ a for a in ana if a in social_types ]
                # We join the labels of the codes related to social relationships levels;
                # if the character is the object of the annotation, we get the inverse of each code
                if len(ana_levels) > 0:
                    if is_object:
                        level = ' ; '.join(map(lambda l: social_levels[social_levels_inverses[l]], ana_levels))
                    else:
                        level = ' ; '.join(map(lambda l: social_levels[l], ana_levels))
                else:
                    level = 'Unspecified'
                # For each code in the ana attribute, we add the related text segment
                # to our characteristics; we add the level or the relations if needed
                for code in ana:
                    # If the character is object and the code is for a familial relationship,
                    # we get the inverse code, according to the character gender if needed
                    if is_object and code in familial_inverses.keys():
                        if isinstance(familial_inverses[code], dict):
                            code = familial_inverses[code][character.gender.id] if character.gender else familial_inverses[code][1]
                        else:
                            code = familial_inverses[code]
                    # If the character is object and the code is for a
                    # social relationship level, we get the inverse code
                    if is_object and code in social_levels_inverses.keys():
                        code = social_levels_inverses[code]
                    # If the character is subject, we add the text segment for each code;
                    # if the character is object, we add it only if the code is for a relation
                    if not is_object or code[:12] == '#PROS-EV-REL':
                        data = { 'content': content, 'url': url,
                                 'in_relation_with': in_relation_with,
                                 'position_percentage' : position_percentage }
                        if code in ana_types:
                            data['level'] = level
                        for category in characteristics:
                            if code in category['codes'].keys():
                                category['codes'][code]['annotations'].setdefault(tcx, []).append(data)
                                category['codes'][code]['nb'] += 1
                                category['nb'] += 1
                        # Special case: if the code is a social relationship level, and no type
                        # is specified, we also add the text segment to the type "Unspecified"
                        if code in social_levels.keys() and len(ana_types) == 0:
                            characteristics[8]['codes']['#PROS-EV-REL-TY-SOC']['annotations'].setdefault(tcx, []).append({
                                'content': content, 'url': url, 'level': level,
                                'in_relation_with': in_relation_with, 'position_percentage' : position_percentage
                            })
                            characteristics[8]['codes']['#PROS-EV-REL-TY-SOC']['nb'] += 1
                            characteristics[8]['nb'] += 1

        characteristics_as_json = self.get_characteristics_as_json(characteristics)

        context['characteristics'] = characteristics
        context['characteristics_as_json'] = characteristics_as_json

    def get_model(self):
        return Bonhum_StoryCharacter

    def get_form(self, request=None):
        initials = None
        if request:
            initials = request.GET
        return FilterCharacters(initials)

    @property
    def key(self):
        return 'characters'

    @property
    def label(self):
        return 'People'

    @property
    def label_singular(self):
        return 'Character'

    # Codes related to a single character (e.g. happy, ascension status, etc.);
    # we return ids of characters annotated as subjects
    def get_ids_by_code(self, soup, code):
        # We get the <rs> annotations including the code in the ana attribute
        spans = soup.find_all('span', attrs={ 'data-dpt': 'rs', 'data-dpt-ana':
                                               re.compile(ur'.*?' + code + ur'\b.*?') })
        # For each annotation, we get the first id in the ref attribute
        # (i.e. the id of the character "subject" of the annotation)
        ids = [ int(span.attrs.get('data-dpt-ref').split(' ')[0][1:]) for span in spans ]
        return ids

    # Codes related to "symmetric" relations (e.g. sibling, hostility, with an equal, etc.);
    # we return ids of characters annotated both as subjects and as objects
    def get_ids_by_symmetric_rel_code(self, soup, code):
        # We get the <rs> annotations including the code in the ana attribute
        spans = soup.find_all('span', attrs={ 'data-dpt': 'rs', 'data-dpt-ana':
                                               re.compile(ur'.*?' + code + ur'\b.*?') })
        ids = []
        # For each annotation, we get all the ids in the ref attribute (i.e. the id of
        # the character "subject" of the annotation, and the ids of the characters "objects")
        for span in spans:
            ref = span.attrs.get('data-dpt-ref').split(' ')
            ids += [ int(id[1:]) for id in ref ]
        return ids

    # Codes related to "asymmetric" relations (e.g. parent/child, with an
    # inferior/superior, etc.); we return ids of characters annotated as subjects with
    # the given code, and ids of characters annotated as objects with the inverse code
    # E.g. when the given code is "relation with an inferior":
    # - A is in relation with an inferior B -> we return A
    # - C is in relation with a superior D -> we return D
    def get_ids_by_asymmetric_rel_code(self, soup, code):
        # We look for the inverse code in social levels and familial relationships
        if code in social_levels_inverses.keys():
            inverse_code = social_levels_inverses[code]
        elif code in familial_inverses.keys():
            inverse_code = familial_inverses[code]
        # Special case: uncle/aunt and nephew/niece are grouped
        elif code in ['ONC-TAN', 'NEV-NIEC']:
            uncle_aunt = '#PROS-EV-REL-TY-FAM-ONC|#PROS-EV-REL-TY-FAM-TAN'
            nephew_niece = '#PROS-EV-REL-TY-FAM-NEV|#PROS-EV-REL-TY-FAM-NIEC'
            if code == 'ONC-TAN':
                code = uncle_aunt
                inverse_code = nephew_niece
            else:
                code = nephew_niece
                inverse_code = uncle_aunt
        # We get the <rs> annotations including the code in the ana attribute
        spans_subject = soup.find_all('span', attrs={ 'data-dpt': 'rs', 'data-dpt-ana':
                                               re.compile(ur'.*?' + code + ur'\b.*?') })
        # For each annotation, we get the first id in the ref attribute
        # (i.e. the id of the character "subject" of the annotation)
        ids = [ int(span.attrs.get('data-dpt-ref').split(' ')[0][1:]) for span in spans_subject ]
        # We get the <rs> annotations including the inverse code in the ana attribute
        spans_object = soup.find_all('span', attrs={ 'data-dpt': 'rs', 'data-dpt-ana':
                                               re.compile(ur'.*?' + inverse_code + ur'\b.*?') })
        # For each annotation, we get the ids of the characters "objects" of the annotation
        # (i.e. all the ids in the ref attribute except the first one)
        for span in spans_object:
            ref = span.attrs.get('data-dpt-ref').split(' ')
            ref.pop(0)
            ids += [ int(id[1:]) for id in ref ]
        return ids

    # Return ids of characters annotated in relation with a specific place
    def get_ids_by_place_id(self, soup, place_id):
        # We get the <placeName> annotations related to the place
        # (i.e. when the ref attribute starts with place_id)
        spans = soup.find_all('span', attrs={ 'data-dpt': 'placeName', 'data-dpt-ref':
                                               re.compile(ur'^#' + place_id + ur'\b.*?') })
        ids = []
        # For each annotation, we get the ids of the related characters (i.e. the ids
        # in the ref attribute, except the first one since it is the one of the place)
        for span in spans:
            ref = span.attrs.get('data-dpt-ref').split(' ')
            ref.pop(0)
            ids += [ int(id[1:]) for id in ref ]
        return ids

    def _build_queryset(self, request, term):
        type = self.key
        query_characters = Bonhum_StoryCharacter.objects.filter(
            Q(name__icontains=term) | \
            # name variants of the character
            Q(bonhum_storycharacternamevariant__name__icontains=term) | \
            Q(type__name__icontains=term) | \
            Q(gender__name__icontains=term) | \
            Q(age__name__icontains=term) | \
            Q(religion__name__icontains=term) | \
            Q(titles__name__icontains=term) | \
            # name of the geographical origin of the character
            Q(geographical_origin__name__icontains=term) | \
            # name variants of the geographical origin of the character
            Q(geographical_origin__bonhum_storyplacenamevariant__name__icontains=term) | \
            Q(traits__name__icontains=term) | \
            Q(occupations__name__icontains=term)
        )

        character_type = request.GET.get('character_type', '')
        gender = request.GET.get('gender', '')
        age = request.GET.get('age', '')
        religion = request.GET.get('religion', '')
        title = request.GET.get('title', '')
        origin = request.GET.get('origin', '')
        trait = request.GET.get('trait', '')
        occupation = request.GET.get('occupation', '')
        status_code = request.GET.get('status', '')
        psychology_code = request.GET.get('psychology', '')
        socio_eco_status_code = request.GET.get('socio_eco_status', '')
        socio_eco_level_code = request.GET.get('socio_eco_level', '')
        culture_code = request.GET.get('culture', '')
        familial_rel_code = request.GET.get('familial_rel', '')
        social_rel_type_code = request.GET.get('social_rel_type', '')
        social_rel_level_code = request.GET.get('social_rel_level', '')
        linked_place_id = request.GET.get('linked_place', '')

        if character_type:
            query_characters = query_characters.filter(type__name=character_type)
        if gender:
            query_characters = query_characters.filter(gender__name=gender)
        if age:
            query_characters = query_characters.filter(age__name=age)
        if religion:
            query_characters = query_characters.filter(religion__name=religion)
        if title:
            query_characters = query_characters.filter(titles__name=title)
        if origin:
            query_characters = query_characters.filter(geographical_origin__name=origin)
        if trait:
            query_characters = query_characters.filter(traits__name=trait)
        if occupation:
            query_characters = query_characters.filter(occupations__name=occupation)

        tcx_contents = TextContentXML.objects.filter(content__isnull=False).values_list('content', flat=True)
        soup = BeautifulSoup(' '.join(tcx_contents), 'lxml')

        if status_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_code(soup, status_code))
        if psychology_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_code(soup, psychology_code))
        if socio_eco_status_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_code(soup, socio_eco_status_code))
        if socio_eco_level_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_code(soup, socio_eco_level_code))
        if culture_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_code(soup, culture_code))
        if familial_rel_code:
            if familial_rel_code in familial_inverses.keys() or familial_rel_code in ['ONC-TAN', 'NEV-NIEC']:
                ids = self.get_ids_by_asymmetric_rel_code(soup, familial_rel_code)
            else:
                ids = self.get_ids_by_symmetric_rel_code(soup, familial_rel_code)
            query_characters = query_characters.filter(id__in=ids)
        if social_rel_type_code:
            query_characters = query_characters.filter(id__in=self.get_ids_by_symmetric_rel_code(soup, social_rel_type_code))
        if social_rel_level_code:
            if social_rel_level_code == '#PROS-EV-REL-TY-SOC-N-AVECP':
                ids = self.get_ids_by_symmetric_rel_code(soup, social_rel_level_code)
            else:
                ids = self.get_ids_by_asymmetric_rel_code(soup, social_rel_level_code)
            query_characters = query_characters.filter(id__in=ids)
        if linked_place_id:
            query_characters = query_characters.filter(id__in=self.get_ids_by_place_id(soup, linked_place_id))

        self._queryset = list(query_characters.distinct().order_by('name').values_list('id', flat=True))

        return self._queryset
