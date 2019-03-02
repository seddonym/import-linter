from importlinter.application.user_options import UserOptions
from importlinter.application.ports import user_options as ports


class UserOptionReader(ports.UserOptionReader):
    def read_options(self) -> UserOptions:
        return UserOptions(
            session_options = {
                'root_package_name': 'grimp',
            },
            contracts_options=[
                {
                    'name': 'Layer contract',
                    'class': 'importlinter.contracts.layers.LayersContract',
                    'containers': [
                       'grimp',
                    ],
                    'layers': [
                        'adaptors',
                        'main',
                        'application',
                        'domain',
                    ],
                },
                {
                    'name': 'Independence contract',
                    'class': 'importlinter.contracts.independence.IndependenceContract',
                    'containers': [
                        'grimp',
                    ],
                    'modules': [
                        'grimp.main',
                        'grimp.domain',
                    ],
                },
            ],
        )
