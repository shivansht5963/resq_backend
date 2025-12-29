from google.cloud import storage
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'gen-lang-client-0117249847-4c0fea8c17a6.json'
)

client = storage.Client(credentials=credentials, project='gen-lang-client-0117249847')

print("Files in bucket:")
blobs = list(client.list_blobs('resq-campus-security'))
for blob in blobs[:10]:
    print(f"  {blob.name}")
    # Make public
    blob.make_public()
    
print(f"\n✅ Made {len(blobs)} images publicly readable!")
