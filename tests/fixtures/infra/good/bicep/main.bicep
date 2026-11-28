// A storage account that refuses plain HTTP, old TLS and anonymous blob access.
param location string = resourceGroup().location

resource store 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'simstore${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}
