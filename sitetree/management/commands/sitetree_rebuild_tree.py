from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS

from sitetree.utils import get_tree_model, import_project_sitetree_modules
from sitetree.settings import APP_MODULE_NAME


MODEL_TREE_CLASS = get_tree_model()


class Command(BaseCommand):

    help = 'Places sitetrees of the project applications (defined in `app_name.sitetree.py`) into DB, replacing old ones if any.'
    args = 'tree_name'
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a specific database to place trees and items into. Defaults to the "default" database.'),
        )

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('The tree_name argument is required!')
        tree_name = args[0]
        # Delete trees with the same name beforehand.
        using = options.get('database', DEFAULT_DB_ALIAS)
        MODEL_TREE_CLASS.objects.filter(alias=tree_name).using(using).delete()
        maintree = MODEL_TREE_CLASS.objects.using(using).create(alias=tree_name)

        tree_modules = import_project_sitetree_modules()

        if not tree_modules:
            self.stdout.write('No sitetrees found in project apps (searched in %%app%%/%s.py).\n' % APP_MODULE_NAME)

        for module in tree_modules:
            sitetrees = getattr(module, 'sitetrees', None)
            app = module.__dict__['__package__']
            if sitetrees is not None:
                self.stdout.write('Sitetrees found in `%s` app ...\n' % app)
                for tree in sitetrees:
                    self.stdout.write('  Processing `%s` tree ...\n' % tree.alias)

                    # Drop id to let the DB handle it.
                    # tree.id = None
                    # tree.save(using=using)
                    for item in tree.dynamic_items:
                        self.stdout.write('    Adding `%s` tree item ...\n' % item.title)
                        # Drop id to let the DB handle it.
                        item.id = None
                        if item.parent is not None:
                            # Suppose parent tree object is already saved to DB.
                            item.parent_id = item.parent.id
                        item.tree = maintree
                        item.save(using=using)
                        if item.access_restricted:
                            item.access_permissions = item.pending_permissions
                            item.save()
