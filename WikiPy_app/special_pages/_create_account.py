import typing as typ

from . import SpecialPage


def load_special_page(settings) -> SpecialPage:
    class CreateAccountPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'create_account', 'Create account')

        def _get_data_impl(self, api, sub_title, request) \
                -> typ.Tuple[typ.Dict[str, typ.Any], typ.Iterable[typ.Any], typ.Optional[str]]:
            get_params = request.GET

            context = {
                'wikicode': api.get_page_content(4, 'Message-CreateAccountDisclaimer'),
            }

            if api.get_param(get_params, 'action') == 'create_account':
                main_page_title = api.as_url_title(api.get_full_page_title(
                    self._settings.MAIN_PAGE_NAMESPACE_ID,
                    self._settings.MAIN_PAGE_TITLE
                ))
                post_params = request.POST
                username = api.get_param(post_params, 'wpy-createaccount-username')
                password = api.get_param(post_params, 'wpy-createaccount-password')
                email = api.get_param(post_params, 'wpy-createaccount-email')

                context['wpy_create_account_username'] = username
                context['wpy_create_account_password'] = password
                context['wpy_create_account_email'] = email

                try:
                    api.create_user(username, password=password, email=email)
                except api.InvalidUsernameError:
                    context['invalid_username'] = True
                except api.DuplicateUsernameError:
                    context['duplicate_username'] = True
                except api.InvalidPasswordError:
                    context['invalid_password'] = True
                except api.InvalidEmailError:
                    context['invalid_email'] = True
                else:
                    context['redirect'] = main_page_title

            return context, [], None

    return CreateAccountPage()
