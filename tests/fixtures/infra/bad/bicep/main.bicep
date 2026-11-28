// Planted defects: plain HTTP allowed, TLS 1.0, anonymous blob access.
param location string = resourceGroup().location

resource store 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'simstore${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: false
    minimumTlsVersion: 'TLS1_0'
    allowBlobPublicAccess: true
  }
}
