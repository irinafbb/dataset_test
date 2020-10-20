import re
import shutil
import os
import requests
import itertools
import json

login_url = 'https://store.acoustery.com/v1/login'
login_header = {'Content-Type': 'application/json'}
scientist_login = '{"login": "adminScientist", "password": "adminScientist"}'
scientist_token = requests.post(login_url, headers=login_header, data=scientist_login).text
scientist_token = re.split('"', scientist_token)[3]
scientist_header = {'Authorization': scientist_token, 'Content-Type': 'application/json'}
url = 'https://store.acoustery.com/v1/datasetv2'

number = 0
if not os.path.exists('sources_single'):
    os.mkdir('sources_single')
rename = open('./rename_all.csv', 'w', encoding='utf-8')
result = open('google_dataset_all.txt', 'w', encoding='utf-8')
data = open(f'./google_single_one.csv', encoding='utf-8')
datalines = data.readlines()
translation = {'Непродуктивный': 'unproductive', 'Продуктивный': 'productive',
               'Сухой/малопродуктивный': 'dry_productive_small', 'Малопродуктивный/влажный': 'wet_productive_small',
               'Навязчивый': 'paroxysmal', 'Ненавязчивый': 'not_paroxysmal',
               'Тяжелый': 'heavy', 'Норма': 'normal', 'Короткий': 'short', 'Удлиненный': 'enlogated',
               'Поверхностный': 'shallow', 'Глубокий': 'deep'}
data_sources = {'Пироговка': 'pirogov_i', 'Опросник TypeForm': 'typeform_i', 'Опросник на сайте': 'site_i',
                'Опросник Гугл': 'google_i', 'Казахстан': 'kazakhstan_i'}
for source in data_sources:
    user = data_sources.get(source, '')
    if not os.path.exists(user):
        os.mkdir(f'./sources_single/{user}')
    data_raw = f'{{"login": "{user}", "password": "cZWkQQQK4MiMtFzq"}}'
    token = requests.post(login_url, headers=login_header, data=data_raw).text
    token = re.split('"', token)[3]
    header = {'Authorization': token}
    for line in datalines:
        line = re.split(',', line)
        if line[4] == source:
            number += 1
            identifier = f'{number}_{user}'
            path = f'./sources_single/{user}/{identifier}_{line[3]}.wav'
            shutil.copy(line[0], path)
            rename.write(f'{line[0]},{path},')
            audio = open(path, 'rb')
            if line[6]:
                age = line[6]
            else:
                age = 0

            if line[3] == 'cough':
                audio_type = 'cough'
                files = {'cough_audio': audio}
            else:
                audio_type = 'breathing'
                files = {'breath_audio': audio}

            if line[7] == 'f':
                gender = 'female'
            else:
                gender = 'male'

            if line[11] == 'yes':
                smoking = 'true'
            else:
                smoking = 'false'

            if line[14] == 'yes':
                sick_days = '30'
            elif line[14] == 'no':
                sick_days = '15'
            else:
                sick_days = '0'

            if line[15].lower() == 'да':
                representative = True
            else:
                representative = False

            if line[16]:
                comment = line[16]
            else:
                comment = None

            if line[16] and re.search('провоцируе|форсир', comment):
                is_forced = 'true'
            else:
                is_forced = 'false'

            productivity = translation.get(line[12].rstrip(), None)
            intensity = translation.get(line[13].rstrip(), None)
            inhale_difficulty = translation.get(line[17], None)
            inhale_duration = translation.get(line[18], None)
            inhale_depth = translation.get(line[19], None)
            exhale_difficulty = translation.get(line[20], None)
            exhale_duration = translation.get(line[21], None)
            exhale_depth = translation.get(line[22], None)
            if line[23] == 'nocovid':
                covid_status = 'no_covid19'
            else:
                if re.search('пневмон|поражен', line[24]):
                    covid_status = 'covid19_severe_symptomatic'
                elif re.search('бессимптомн', line[24]):
                    covid_status = 'covid19_without_symptomatic'
                else:
                    covid_status = 'covid19_mild_symptomatic'

            other = None
            if line[24] == 'Здоров' or line[24] == '':
                disease_type = 'none'
                disease = None
            elif re.search('ХОБЛ|Астма|роническ', line[24]):
                disease_type = 'chronic'
                if re.search('ХОБЛ', line[24]):
                    disease = 'copd'
                elif re.search('Астма', line[24]):
                    disease = 'bronchial_asthma'
                elif re.search('бронхит', line[24]):
                    disease = 'chronical_bronchitis'
                else:
                    disease = 'other'
                    other = line[24].encode('utf-8')
            elif re.search('невмони|острый', line[24]):
                disease_type = 'acute'
                if re.search('невмони', line[24]):
                    disease = 'pneumonia'
                elif re.search('острый', line[24]):
                    disease = 'acute_bronchitis'
            else:
                disease_type = 'acute'
                disease = 'other'
                other = line[24].encode('utf-8')

            dataset = {'identifier': identifier, 'age': age, 'gender': gender, 'is_smoking': smoking,
                       'disease_type': disease_type, 'disease': disease, 'other_disease_name': other,
                       'sick_days': sick_days, 'covid19_symptomatic_type': covid_status, 'is_force': is_forced,
                       'privacy_eula_version': '1'}
            dataset_request = requests.post(url, headers=header, data=dataset, files=files).text
            result.write(f'{number}\n{dataset}\n')
            print(f'{number}\n{dataset_request}')
            request_id = re.split('\W+', dataset_request)[2]

            marking_url = f'https://store.acoustery.com/v1/admin/marking/{request_id}/{audio_type}/episodes'
            types_url = f'https://store.acoustery.com/v1/admin/marking/{request_id}/{audio_type}/detailed'
            marking_status = 'not_ready'
            doctor_status = 'not_ready'
            if audio_type == 'cough':
                if re.search('\d', line[27]):
                    marking_status = 'done'
                    cough_marking = '{"episodes": [{'
                    coughs = re.split(' ', line[27].rstrip())
                    for cough in coughs:
                        c_start = re.split('-', cough)[0]
                        c_end = re.split('-', cough)[1]
                        cough_marking += f'"start": {c_start}, "end": {c_end}, "type": "other"'
                        cough_marking += '}, {'
                    cough_marking = cough_marking[:-3] + ']}'
                    result.write(f'{cough_marking}\n')
                    mark_request = requests.put(marking_url, headers=scientist_header, data=cough_marking).status_code
                else:
                    mark_request = 'null'

                if (line[12] and line[13]) or line[16]:
                    doctor_status = 'done'
                cough_types = {'intensity': intensity, 'productivity': productivity, 'commentary': comment,
                               'audio_params': {'is_representative': representative}}
                cough_types = json.dumps(cough_types)
                result.write(f'{cough_types}\n')
                types_request = requests.patch(types_url, headers=scientist_header,
                                               data=cough_types.encode('utf-8')).status_code
            if audio_type == 'breathing':
                if re.search('\d', line[25]) and re.search('\d', line[26]):
                    marking_status = 'done'
                    breath_marking = '{"episodes": [{'
                    inhales = re.split(' ', line[25].rstrip())
                    exhales = re.split(' ', line[26].rstrip())
                    for sound in itertools.chain(inhales, exhales):
                        if sound in inhales:
                            breath_type = 'breathing_inhale'
                        else:
                            breath_type = 'breathing_exhale'
                        start = re.split('-', sound)[0]
                        end = re.split('-', sound)[1]
                        breath_marking += f'"start": {start}, "end": {end}, "type": "{breath_type}"'
                        breath_marking += '}, {'
                    breath_marking = breath_marking[:-3] + ']}'
                    result.write(f'{breath_marking}\n')
                    mark_request = requests.put(marking_url, headers=scientist_header, data=breath_marking).status_code
                else:
                    mark_request = 'null'

                if line[17] and line[18] and line[19] and line[20] and line[21] and line[22]:
                    doctor_status = 'done'
                breathing_types = {'inhale': {'depth_type': inhale_depth, 'duration_type': inhale_duration,
                                              'difficulty_type': inhale_difficulty},
                                   'exhale': {'depth_type': exhale_depth, 'duration_type': exhale_duration,
                                              'difficulty_type': exhale_difficulty}, 'commentary': comment,
                                   'audio_params': {'is_representative': representative}}
                breathing_types = json.dumps(breathing_types)
                result.write(f'{breathing_types}\n')
                types_request = requests.patch(types_url, headers=scientist_header,
                                               data=breathing_types.encode('utf-8')).status_code

            status_url = f'https://store.acoustery.com/v1/admin/marking/{request_id}'
            status_data = f'{{"doctor_status": "{doctor_status}", "marking_status": "{marking_status}"}}'
            result.write(f'{status_data}\n')
            status_request = requests.patch(status_url, headers=scientist_header, data=status_data).status_code
            print(f'{identifier} {mark_request} {types_request} {status_request}')
            rename.write(f'{request_id},{mark_request},{types_request},{status_request}\n')

rename.close()
result.close()
