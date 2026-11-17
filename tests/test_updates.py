from update_ui import installer_for_release, PREFIX, version


def release(tag='v1.8.8'):
    name = 'Olney_Engine_Setup_' + tag[1:] + '.exe'
    return {'tag_name': tag, 'draft': False, 'prerelease': False,
            'assets': [{'name': name, 'browser_download_url': PREFIX + tag + '/' + name}]}


def test_only_new_stable_releases_offer_official_installer():
    data = release()
    assert installer_for_release(data, '1.8.7')[0] == 'v1.8.8'
    assert installer_for_release(data, '1.8.8') is None
    assert installer_for_release(data, '1.9.0') is None
    assert version('v1.10.0') > version('1.9.9')


def test_missing_and_external_installers_are_rejected():
    for value in [[], {}, {'tag_name': None}, {'tag_name': 'v1.8.8', 'assets': []}]:
        try:
            installer_for_release(value, '1.8.7')
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed release accepted')
    for url in ['https://example.org/setup.exe', PREFIX + 'v1.8.8/unexpected.exe']:
        data = release()
        data['assets'][0]['browser_download_url'] = url
        try:
            installer_for_release(data, '1.8.7')
        except ValueError:
            pass
        else:
            raise AssertionError('Unexpected installer accepted')


def test_draft_and_prerelease_are_not_offered():
    for flag in ['draft', 'prerelease']:
        data = release()
        data[flag] = True
        try:
            installer_for_release(data, '1.8.7')
        except ValueError:
            pass
        else:
            raise AssertionError('Non-stable release accepted')
