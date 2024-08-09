from mac_vendor_lookup import MacLookup, BaseMacLookup
# Updates the MAC OUI database and stores it locally in a file called mac-vendors.txt
# Runs each time the sp_device_inventory is kicked off

def update_oui():
    BaseMacLookup.cache_path = "./mac-vendors.txt"
    mac = MacLookup()
    mac.update_vendors()  # <- This can take a few seconds for the download and it will be stored in the new path
    print('OUI Vendor List Updated!')


if __name__ == "__main__":
    update_oui
