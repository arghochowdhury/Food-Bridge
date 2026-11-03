from django.core.management.base import BaseCommand

from core.models import District, Division, PostOffice, Thana, Upazila

DISTRICTS = {
    "Barishal": ["Barguna", "Barishal", "Bhola", "Jhalokati", "Patuakhali", "Pirojpur"],
    "Chattogram": ["Bandarban", "Brahmanbaria", "Chandpur", "Chattogram", "Cumilla", "Cox's Bazar",
                   "Feni", "Khagrachhari", "Lakshmipur", "Noakhali", "Rangamati"],
    "Dhaka": ["Dhaka", "Faridpur", "Gazipur", "Gopalganj", "Kishoreganj", "Madaripur", "Manikganj",
              "Munshiganj", "Narayanganj", "Narsingdi", "Rajbari", "Shariatpur", "Tangail"],
    "Khulna": ["Bagerhat", "Chuadanga", "Jashore", "Jhenaidah", "Khulna", "Kushtia", "Magura",
               "Meherpur", "Narail", "Satkhira"],
    "Mymensingh": ["Jamalpur", "Mymensingh", "Netrokona", "Sherpur"],
    "Rajshahi": ["Bogura", "Chapainawabganj", "Joypurhat", "Naogaon", "Natore", "Pabna", "Rajshahi", "Sirajganj"],
    "Rangpur": ["Dinajpur", "Gaibandha", "Kurigram", "Lalmonirhat", "Nilphamari", "Panchagarh", "Rangpur", "Thakurgaon"],
    "Sylhet": ["Habiganj", "Moulvibazar", "Sunamganj", "Sylhet"],
}

# Small sample so you can test the full cascade. Add the rest from the admin panel
# or load a complete dataset of upazila / thana / post offices.
SAMPLE = {
    ("Chattogram", "Chattogram"): {
        "Chattogram Sadar": {
            "Kotwali": ["Chattogram GPO", "Chawkbazar"],
            "Pahartali": ["Pahartali", "Firozshah Colony"],
            "Panchlaish": ["Panchlaish", "Chattogram Cantonment"],
            "Khulshi": ["Khulshi", "Lalkhan Bazar"],
        },
        "Hathazari": {"Hathazari": ["Hathazari", "Fatehpur"]},
        "Sitakunda": {"Sitakunda": ["Sitakunda", "Barabkunda"]},
    },
    ("Chattogram", "Cox's Bazar"): {
        "Cox's Bazar Sadar": {"Cox's Bazar Sadar": ["Cox's Bazar", "Jhilongja"]},
    },
    ("Dhaka", "Dhaka"): {
        "Dhaka City": {
            "Dhanmondi": ["Dhanmondi", "New Market"],
            "Gulshan": ["Gulshan Model Town", "Banani"],
            "Mirpur": ["Mirpur", "Mirpur Colony"],
        },
        "Savar": {"Savar": ["Savar", "Savar Cantonment"]},
    },
    ("Sylhet", "Sylhet"): {
        "Sylhet Sadar": {"Kotwali": ["Sylhet Sadar", "Ambarkhana"]},
    },
}


class Command(BaseCommand):
    help = "Load divisions, districts and sample upazila / thana / post office data."

    def handle(self, *args, **options):
        for div_name, districts in DISTRICTS.items():
            div, _ = Division.objects.get_or_create(name=div_name)
            for d in districts:
                District.objects.get_or_create(division=div, name=d)
        for (div_name, dist_name), upazilas in SAMPLE.items():
            dist = District.objects.get(division__name=div_name, name=dist_name)
            for up_name, thanas in upazilas.items():
                up, _ = Upazila.objects.get_or_create(district=dist, name=up_name)
                for th_name, offices in thanas.items():
                    th, _ = Thana.objects.get_or_create(upazila=up, name=th_name)
                    for po in offices:
                        PostOffice.objects.get_or_create(thana=th, name=po)
        self.stdout.write(self.style.SUCCESS("Location data loaded."))
