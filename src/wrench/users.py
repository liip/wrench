from collections import namedtuple

GpgKey = namedtuple('GpgKey', 'id fingerprint armored_key')
User = namedtuple('User', 'id username first_name last_name groups_ids gpg_key')
Group = namedtuple('Group', 'id name members_ids')
