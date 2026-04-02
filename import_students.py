#!/usr/bin/env python
"""
Bulk import JIMS MCA batch 2025-27 students into the database
"""

from app import create_app, db
from app.models import User

# Student data from the provided PDF
students_data = [
    ("Pratyush", "Vashishtha", "pratyush_vashishtha_mca25@jimsipu.org"),
    ("Ashwani", "Kumar Puri", "ashwani_kumar_puri_mca25@jimsipu.org"),
    ("Aditya", "Basu", "aditya_basu_mca25@jimsipu.org"),
    ("Mayank", "Tyagi", "mayank_tyagi_mca25@jimsipu.org"),
    ("Mehak", "Garg", "mehak_garg_mca25@jimsipu.org"),
    ("Aman", "jimsipu", "aman_jimsipu_mca25@jimsipu.org"),
    ("Mehak", "Baisoya", "mehak_baisoya_mca25@jimsipu.org"),
    ("Ayush", "Mishra", "ayush_mishra_mca25@jimsipu.org"),
    ("Vansh", "Vij", "vansh_vij_mca25@jimsipu.org"),
    ("Krish", "Khandelwal", "krish_khandelwal_mca25@jimsipu.org"),
    ("Adiva", "jimsipu", "adiva_jimsipu_mca25@jimsipu.org"),
    ("Sanskriti", "jimsipu", "sanskriti_jimsipu_mca25@jimsipu.org"),
    ("Piyush", "Verma", "piyush_verma_mca25@jimsipu.org"),
    ("Raunaq", "Gupta", "raunaq_gupta_mca25@jimsipu.org"),
    ("Anshika", "Jain", "anshika_jain_mca25@jimsipu.org"),
    ("Paarth", "Kumar", "paarth_kumar_mca25@jimsipu.org"),
    ("Yashika", "Bedi", "yashika_bedi_mca25@jimsipu.org"),
    ("Vidushi", "Arora", "vidushi_arora_mca25@jimsipu.org"),
    ("Naina", "jimsipu", "naina_jimsipu_mca25@jimsipu.org"),
    ("Varun", "Sharma", "varun_sharma_mca25@jimsipu.org"),
    ("Gaurav", "Arora", "gaurav_arora_mca25@jimsipu.org"),
    ("Shahnawaaz", "Hussain", "shahnawaaz_hussain_mca25@jimsipu.org"),
    ("Yuvraj", "Paudel", "yuvraj_paudel_mca25@jimsipu.org"),
    ("Vertika", "Singh", "vertika_singh_mca25@jimsipu.org"),
    ("Raghav", "Tyagi", "raghav_tyagi_mca25@jimsipu.org"),
    ("Abhipriya", "Bhardwaj", "abhipriya_bhardwaj_mca25@jimsipu.org"),
    ("Adarsh", "Sharma", "adarsh_sharma_mca25@jimsipu.org"),
    ("Kunal", "Gupta", "kunal_gupta_mca25@jimsipu.org"),
    ("Nipun", "Gupta", "nipun_gupta_mca25@jimsipu.org"),
    ("Jai", "Vijayran", "jai_vijayran_mca25@jimsipu.org"),
    ("Shailly", "Panwar", "shailly_panwar_mca25@jimsipu.org"),
    ("Bhavishay", "jimsipu", "bhavishay_jimsipu_mca25@jimsipu.org"),
    ("Rishabh", "Verma", "rishabh_verma_mca25@jimsipu.org"),
    ("Neha", "jimsipu", "neha_jimsipu_mca25@jimsipu.org"),
    ("R", "Kartikeyan", "r_kartikeyan_mca25@jimsipu.org"),
    ("Aastha", "Setia", "aastha_setia_mca25@jimsipu.org"),
    ("Bhavya", "Bhutani", "bhavya_bhutani_mca25@jimsipu.org"),
    ("Abhishek", "Bhalla", "abhishek_bhalla_mca25@jimsipu.org"),
    ("Priyanshu", "Rana", "priyanshu_rana_mca25@jimsipu.org"),
    ("Khushi", "jimsipu", "khushi_jimsipu_mca25@jimsipu.org"),
    ("Mayur", "Prabhakar Suryawanshi", "mayur_prabhakar_suryawanshi_mca25@jimsipu.org"),
    ("Shreshthi", "Suman", "shreshthi_suman_mca25@jimsipu.org"),
    ("Priyanshu", "Mittal", "priyanshu_mittal_mca25@jimsipu.org"),
    ("Daksh", "Rathi", "daksh_rathi_mca25@jimsipu.org"),
    ("Aditya", "jimsipu", "aditya_jimsipu_mca25@jimsipu.org"),
    ("Rishabh", "Rustagi", "rishabh_rustagi_mca25@jimsipu.org"),
    ("Vaani", "Rana", "vaani_rana_mca25@jimsipu.org"),
    ("Aditi", "Tanwar", "aditi_tanwar_mca25@jimsipu.org"),
    ("Mayank", "Sharma", "mayank_sharma_mca25@jimsipu.org"),
    ("Kanan", "jimsipu", "kanan_jimsipu_mca25@jimsipu.org"),
    ("Paras", "Sharma", "paras_sharma_mca25@jimsipu.org"),
    ("Mir", "Anish", "mir_anish_mca25@jimsipu.org"),
    ("Harsh", "Jain", "harsh_jain_mca25@jimsipu.org"),
    ("Gagandeep", "Singh", "gagandeep_singh_mca25@jimsipu.org"),
    ("Kaushal", "Kumar", "kaushal_kumar_mca25@jimsipu.org"),
    ("Saransh", "Thanik", "saransh_thanik_mca25@jimsipu.org"),
    ("Namit", "Joshi", "namit_joshi_mca25@jimsipu.org"),
    ("Shankar", "Suman Singh Parmar", "shankar_suman_singh_parmar_mca25@jimsipu.org"),
    ("Gaurav", "Kumar", "gaurav_kumar_mca25@jimsipu.org"),
    ("Prashant", "Shukla", "prashant_shukla_mca25@jimsipu.org"),
    ("Vaibhav", "Gupta", "vaibhav_gupta_mca25@jimsipu.org"),
    ("Manish", "Kumar", "manish_kumar_mca25@jimsipu.org"),
    ("Ananya", "Arora", "ananya_arora_mca25@jimsipu.org"),
    ("Varun", "Malik", "varun_malik_mca25@jimsipu.org"),
    ("Mahak", "Arora", "mahak_arora_mca25@jimsipu.org"),
    ("Pushpansh", "Pandey", "pushpansh_pandey_mca25@jimsipu.org"),
    ("Tarun", "Vashishth", "tarun_vashishth_mca25@jimsipu.org"),
    ("Vanshika", "Gupta", "vanshika_gupta_mca25@jimsipu.org"),
    ("Anshul", "Sharma", "anshul_sharma_mca25@jimsipu.org"),
    ("Makhija", "Charmi Nareshbhai", "makhija_charmi_nareshbhai_mca25@jimsipu.org"),
    ("Ujjawal", "Parashar", "ujjawal_parashar_mca25@jimsipu.org"),
    ("Vidhi", "Singhal", "vidhi_singhal_mca25@jimsipu.org"),
    ("Rahul", "Bhatiya", "rahul_bhatiya_mca25@jimsipu.org"),
    ("Ashneet", "Kaur Kochhar", "ashneet_kaur_kochhar_mca25@jimsipu.org"),
    ("Priyanshu", "Mohta", "priyanshu_mohta_mca25@jimsipu.org"),
    ("Ajeet", "Singh", "ajeet_singh_mca25@jimsipu.org"),
    ("Siddharth", "Gupta", "siddharth_gupta_mca25@jimsipu.org"),
    ("Sheffali", "Sethi", "sheffali_sethi_mca25@jimsipu.org"),
    ("Dimple", "Dhaulakhandi", "dimple_dhaulakhandi_mca25@jimsipu.org"),
    ("Sarvesh", "Bhardwaj", "sarvesh_bhardwaj_mca25@jimsipu.org"),
    ("Kritika", "Gupta", "kritika_gupta_mca25@jimsipu.org"),
    ("Prabhjyot", "Singh", "prabhjyot_singh_mca25@jimsipu.org"),
    ("Manisha", "Sharma", "manisha_sharma_mca25@jimsipu.org"),
    ("Ayush", "Gandhi", "ayush_gandhi_mca25@jimsipu.org"),
    ("Naman", "Gupta", "naman_gupta_mca25@jimsipu.org"),
    ("Vaibhav", "Sharma", "vaibhav_sharma_mca25@jimsipu.org"),
    ("Anurag", "Rathore", "anurag_rathore_mca25@jimsipu.org"),
    ("Hardik", "Dhawan", "hardik_dhawan_mca25@jimsipu.org"),
    ("Rohan", "Kumar Rawat", "rohan_kumar_rawat_mca25@jimsipu.org"),
    ("Manya", "Mittal", "manya_mittal_mca25@jimsipu.org"),
    ("Sanyam", "Kumar", "sanyam_kumar_mca25@jimsipu.org"),
    ("Shivam", "Gupta", "shivam_gupta_mca25@jimsipu.org"),
    ("Rahul", "jimsipu", "rahul_jimsipu_mca25@jimsipu.org"),
    ("Varun", "Bundela", "varun_bundela_mca25@jimsipu.org"),
    ("Abhimanyu", "Khokhar", "abhimanyu_khokhar_mca25@jimsipu.org"),
    ("Vanshika", "jimsipu", "vanshika_jimsipu_mca25@jimsipu.org"),
    ("Pallak", "Anand", "pallak_anand_mca25@jimsipu.org"),
    ("Kashish", "Sanwal", "kashish_sanwal_mca25@jimsipu.org"),
    ("Samikshya", "Ray", "samikshya_ray_mca25@jimsipu.org"),
    ("Tanishk", "Pahwa", "tanishk_pahwa_mca25@jimsipu.org"),
    ("Manya", "Gupta", "manya_gupta_mca25@jimsipu.org"),
    ("Avighyat", "Srivastav", "avighyat_srivastav_mca25@jimsipu.org"),
    ("Kashish", "jimsipu", "kashish_jimsipu_mca25@jimsipu.org"),
    ("Yash", "Tyagi", "yash_tyagi_mca25@jimsipu.org"),
    ("Vibhor", "jimsipu", "vibhor_jimsipu_mca25@jimsipu.org"),
    ("Kritika", "Yadav", "kritika_yadav_mca25@jimsipu.org"),
    ("Akash", "Budhiraja", "akash_budhiraja_mca25@jimsipu.org"),
    ("Jyoti", "Bisht", "jyoti_bisht_mca25@jimsipu.org"),
    ("Ishita", "Dass", "ishita_dass_mca25@jimsipu.org"),
    ("Nikhil", "Kumar Luhaniya", "nikhil_kumar_luhaniya_mca25@jimsipu.org"),
    ("Varun", "Wason", "varun_wason_mca25@jimsipu.org"),
    ("Aarya", "Krishnan", "aarya_krishnan_mca25@jimsipu.org"),
    ("Shivam", "Pal", "shivam_pal_mca25@jimsipu.org"),
    ("Ishaan", "Sharma", "ishaan_sharma_mca25@jimsipu.org"),
    ("Akshit", "Chawla", "akshit_chawla_mca25@jimsipu.org"),
    ("Vansh", "Goyal", "vansh_goyal_mca25@jimsipu.org"),
    ("Khushi", "Kapoor", "khushi_kapoor_mca25@jimsipu.org"),
    ("Aayush", "Kansal", "aayush_kansal_mca25@jimsipu.org"),
    ("Deepika", "Thapliyal", "deepika_thapliyal_mca25@jimsipu.org"),
    ("Karandeep", "Singh", "karandeep_singh_mca25@jimsipu.org"),
    ("Manan", "Sehgal", "manan_sehgal_mca25@jimsipu.org"),
    ("Sahil", "Kumar", "sahil_kumar_mca25@jimsipu.org"),
    ("Chhavi", "Takroo", "chhavi_takroo_mca25@jimsipu.org"),
    ("Harsh", "Gupta", "harsh_gupta_mca25@jimsipu.org"),
    ("Varun", "Bhatia", "varun_bhatia_mca25@jimsipu.org"),
    ("Raskirat", "Singh Manchanda", "raskirat_singh_manchanda_mca25@jimsipu.org"),
    ("Vansh", "jimsipu", "vansh_jimsipu_mca25@jimsipu.org"),
    ("Tushar", "Vashisht", "tushar_vashisht_mca25@jimsipu.org"),
    ("Deepanshu", "jimsipu", "deepanshu_jimsipu_mca25@jimsipu.org"),
    ("Ansh", "Tanwar", "ansh_tanwar_mca25@jimsipu.org"),
    ("Shaurya", "Sharma", "shaurya_sharma_mca25@jimsipu.org"),
    ("Dhruv", "Bhatia", "dhruv_bhatia_mca25@jimsipu.org"),
    ("Abhay", "Garg", "abhay_garg_mca25@jimsipu.org"),
    ("Dhruv", "Malhotra", "dhruv_malhotra_mca25@jimsipu.org"),
    ("Khemendra", "Singh Khangarot", "khemendra_singh_khangarot_mca25@jimsipu.org"),
    ("Arpit", "Bansal", "arpit_bansal_mca25@jimsipu.org"),
    ("Tamanna", "jimsipu", "tamanna_jimsipu_mca25@jimsipu.org"),
    ("Ishika", "Jindal", "ishika_jindal_mca25@jimsipu.org"),
    ("Silky", "Nijhawan", "silky_nijhawan_mca25@jimsipu.org"),
    ("Gautam", "Garg", "gautam_garg_mca25@jimsipu.org"),
    ("Satvik", "Kapoor", "satvik_kapoor_mca25@jimsipu.org"),
    ("Ayush", "Kothari", "ayush_kothari_mca25@jimsipu.org"),
    ("Mohit", "jimsipu", "mohit_jimsipu_mca25@jimsipu.org"),
    ("Jaiyant", "Singh Rawat", "jaiyant_singh_rawat_mca25@jimsipu.org"),
    ("Divyanshi", "Singh", "divyanshi_singh_mca25@jimsipu.org"),
    ("Rupanshi", "Varshney", "rupanshi_varshney_mca25@jimsipu.org"),
    ("Diya", "Jain", "diya_jain_mca25@jimsipu.org"),
    ("Shivansh", "Chhibber", "shivansh_chhibber_mca25@jimsipu.org"),
    ("Ridhima", "Tripathi", "ridhima_tripathi_mca25@jimsipu.org"),
    ("Harsimar", "Singh", "harsimar_singh_mca25@jimsipu.org"),
    ("Lakshay", "jimsipu", "lakshay_jimsipu_mca25@jimsipu.org"),
    ("Shreya", "Singhal", "shreya_singhal_mca25@jimsipu.org"),
    ("Shubham", "Rana", "shubham_rana_mca25@jimsipu.org"),
    ("Jiya", "Jaisingh", "jiya_jaisingh_mca25@jimsipu.org"),
    ("Nikhil", "jimsipu", "nikhil_jimsipu_mca25@jimsipu.org"),
    ("Aditya", "Singh", "aditya_singh_mca25@jimsipu.org"),
    ("Pranay", "Kasana", "pranay_kasana_mca25@jimsipu.org"),
    ("Aniket", "Singhal", "aniket_singhal_mca25@jimsipu.org"),
    ("Mohit", "Sharma", "mohit_sharma_mca25@jimsipu.org"),
    ("Rishi", "Tomer", "rishi_tomer_mca25@jimsipu.org"),
    ("Rishabh", "Devrani", "rishabh_devrani_mca25@jimsipu.org"),
    ("Chhavi", "Vats", "chhavi_vats_mca25@jimsipu.org"),
    ("Paras", "jimsipu", "paras_jimsipu_mca25@jimsipu.org"),
    ("Ashutosh", "Mishra", "ashutosh_mishra_mca25@jimsipu.org"),
]

def import_students():
    """Import all students into the database"""
    app = create_app('development')
    
    with app.app_context():
        print("\n" + "="*60)
        print("IMPORTING JIMS MCA BATCH 2025-27 STUDENTS")
        print("="*60)
        
        imported = 0
        skipped = 0
        password = "jims@123456"
        
        for first_name, last_name, email in students_data:
            try:
                # Extract username from email
                username = email.split('@')[0]
                full_name = f"{first_name} {last_name}"
                
                # Check if user already exists
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    print(f"⊘ Skipping: {full_name} ({username}) - Already exists")
                    skipped += 1
                    continue
                
                # Create new student user
                user = User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role='student',
                    is_active=True
                )
                user.set_password(password)
                
                db.session.add(user)
                imported += 1
                print(f"✓ Added: {full_name} ({username})")
                
            except Exception as e:
                print(f"✗ Error: {first_name} {last_name} - {str(e)}")
                skipped += 1
        
        try:
            db.session.commit()
            print("\n" + "="*60)
            print(f"✓ Import Complete!")
            print(f"  - Successfully imported: {imported} students")
            print(f"  - Skipped: {skipped} (already exist)")
            print(f"  - Total: {imported + skipped}")
            print("="*60)
            print(f"\n🔑 Default Password for all students: {password}\n")
        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error committing to database: {str(e)}")

if __name__ == '__main__':
    import_students()
