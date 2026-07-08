"""
Medical Knowledge Base for RAG System
Contains verified medical information organized by categories.
"""

from typing import List, Dict

# Medical Knowledge Documents
MEDICAL_DOCUMENTS: List[Dict[str, str]] = [
    # Common Symptoms and General Information
    {
        "title": "Headache - General Information",
        "category": "symptoms",
        "content": """
Headache is a common symptom that can be caused by various factors including stress, tension, dehydration, lack of sleep, eye strain, or sinus problems. Most headaches are not serious and can be managed with over-the-counter pain relievers like acetaminophen or ibuprofen. However, certain types of headaches require medical attention.

Warning signs that require immediate medical evaluation:
- Sudden, severe headache (worst headache of your life)
- Headache with fever, stiff neck, confusion, or seizures
- Headache following head injury
- New onset headache in people over 50
- Headache with neurological symptoms like weakness or vision changes

Common triggers: Stress, lack of sleep, dehydration, certain foods, bright lights, strong odors, weather changes.

Management: Rest in a quiet, dark room, apply cold or warm compress, maintain hydration, regular sleep schedule, stress management techniques.
"""
    },

    {
        "title": "Fever - Understanding Body Temperature",
        "category": "symptoms",
        "content": """
Fever is when body temperature rises above the normal range of 97-99°F (36.1-37.2°C). It's usually a sign that the immune system is fighting an infection.

Common causes: Viral infections (most common), bacterial infections, inflammatory conditions, heat exhaustion, certain medications, immunizations.

When to seek medical attention:
- Infants under 3 months with any fever
- Children 3-36 months with fever over 102°F (38.9°C)
- Adults with fever over 103°F (39.4°C) or lasting more than 3 days
- Fever accompanied by severe headache, stiff neck, confusion, persistent vomiting, difficulty breathing, or chest pain

Management: Rest, fluids, acetaminophen or ibuprofen (follow age-appropriate dosing), cool compresses. Never give aspirin to children due to risk of Reye's syndrome.
"""
    },

    {
        "title": "Chest Pain - Cardiac Warning Signs",
        "category": "cardiac",
        "content": """
Chest pain is a serious symptom that requires immediate medical evaluation. It can indicate heart problems, but can also be caused by other conditions like acid reflux, muscle strain, or anxiety.

Heart attack warning signs:
- Pressure, tightness, squeezing, or crushing pain in center of chest lasting more than a few minutes
- Pain radiating to arms (especially left), back, neck, jaw, or stomach
- Shortness of breath, sweating, nausea, lightheadedness
- Women may experience unusual fatigue, sleep disturbances, or indigestion

Other causes: Angina (chest pain from reduced blood flow), pericarditis, pulmonary embolism, pneumonia, panic attacks, gastrointestinal issues.

Emergency: Call emergency services immediately for suspected heart attack. Do not drive yourself.
"""
    },

    {
        "title": "Shortness of Breath - Respiratory Assessment",
        "category": "respiratory",
        "content": """
Shortness of breath (dyspnea) is difficulty breathing or feeling like you can't get enough air. It can range from mild to life-threatening.

Common causes:
- Respiratory: Asthma, COPD, pneumonia, bronchitis, pulmonary embolism
- Cardiac: Heart failure, heart attack, arrhythmias
- Other: Anxiety, anemia, obesity, deconditioning

When to seek emergency care:
- Sudden onset severe shortness of breath
- Difficulty speaking in full sentences
- Blue lips or fingernails (cyanosis)
- Chest pain, confusion, or loss of consciousness
- Pre-existing lung or heart conditions with worsening symptoms

Management: Sit upright, use prescribed inhalers, rest, call emergency services if severe.
"""
    },

    {
        "title": "Abdominal Pain - Gastrointestinal Assessment",
        "category": "gastrointestinal",
        "content": """
Abdominal pain can originate from various organs including stomach, intestines, liver, gallbladder, kidneys, or reproductive organs.

Common patterns:
- Upper right: Gallbladder, liver
- Upper middle: Stomach, duodenum
- Upper left: Spleen, stomach, pancreas
- Lower right: Appendix, ovary, colon
- Lower left: Colon, ovary
- Diffuse: Gastroenteritis, peritonitis, bowel obstruction

Red flags requiring immediate evaluation:
- Severe pain with vomiting
- Blood in stool or vomit
- Fever with abdominal pain
- Signs of dehydration
- Pain lasting more than 24-48 hours
- Recent abdominal surgery or trauma

Management depends on cause but generally includes rest, clear fluids, avoiding solid foods until evaluated.
"""
    },

    {
        "title": "Fatigue - Common Causes and Evaluation",
        "category": "general",
        "content": """
Fatigue is extreme tiredness that doesn't improve with rest. It's a common symptom with many possible causes.

Common causes:
- Lifestyle: Poor sleep, overwork, stress, poor nutrition
- Medical: Anemia, thyroid disorders, diabetes, depression, infections, heart disease, sleep disorders
- Medications: Some drugs cause fatigue as a side effect

When to evaluate:
- Fatigue lasting more than 2 weeks
- Associated with other symptoms (fever, weight loss, pain)
- Interfering with daily activities
- New onset in previously healthy person

Management: Adequate sleep (7-9 hours), regular exercise, balanced diet, stress reduction, treat underlying conditions.
"""
    },

    {
        "title": "Hypertension - Blood Pressure Management",
        "category": "cardiac",
        "content": """
Hypertension (high blood pressure) is a major risk factor for heart disease, stroke, and kidney disease. It's often called the 'silent killer' because it usually has no symptoms.

Blood pressure categories:
- Normal: < 120/80 mmHg
- Elevated: 120-129 (systolic) and < 80 (diastolic)
- Stage 1: 130-139/80-89
- Stage 2: ≥ 140/≥ 90
- Crisis: > 180/> 120

Lifestyle modifications:
- DASH diet (fruits, vegetables, low-fat dairy, whole grains)
- Reduce sodium intake (< 2,300 mg/day, ideally < 1,500 mg)
- Regular physical activity (150 minutes moderate exercise/week)
- Maintain healthy weight
- Limit alcohol and quit smoking
- Stress management

Regular monitoring and medication if prescribed by healthcare provider.
"""
    },

    {
        "title": "Diabetes - Blood Sugar Management",
        "category": "endocrine",
        "content": """
Diabetes mellitus is a condition where the body cannot properly regulate blood sugar (glucose).

Type 1: Autoimmune destruction of insulin-producing cells, usually diagnosed in childhood
Type 2: Insulin resistance, most common form, often lifestyle-related
Gestational: Occurs during pregnancy

Symptoms: Frequent urination, excessive thirst, unexplained weight loss, increased hunger, fatigue, slow-healing sores, frequent infections, blurred vision.

Management:
- Blood sugar monitoring
- Healthy eating (balanced carbohydrates, fiber, healthy fats)
- Regular physical activity
- Weight management
- Medications as prescribed (oral medications, insulin)
- Regular medical follow-up

Complications can be prevented with good control: eye problems, kidney disease, nerve damage, heart disease, foot problems.
"""
    },

    {
        "title": "Mental Health - Depression and Anxiety",
        "category": "mental_health",
        "content": """
Mental health conditions affect thoughts, feelings, and behaviors. Depression and anxiety are common and treatable.

Depression symptoms:
- Persistent sadness, hopelessness
- Loss of interest in activities
- Changes in sleep, appetite, energy
- Difficulty concentrating
- Feelings of worthlessness or guilt
- Thoughts of death or suicide

Anxiety symptoms:
- Excessive worry or fear
- Restlessness, feeling on edge
- Rapid heartbeat, sweating, trembling
- Fatigue, difficulty concentrating
- Sleep disturbances
- Avoidance of certain situations

Treatment approaches:
- Psychotherapy (cognitive behavioral therapy)
- Medications when appropriate
- Lifestyle changes (exercise, sleep, nutrition)
- Stress management techniques
- Support groups and counseling

Seek professional help if symptoms interfere with daily functioning or include suicidal thoughts.
"""
    },

    {
        "title": "Infectious Diseases - Common Viral Infections",
        "category": "infectious",
        "content": """
Viral infections are caused by viruses and are usually self-limiting but can sometimes be serious.

Common viral infections:
- Common cold: Rhinovirus, coronavirus - symptoms include runny nose, sore throat, cough, mild fever
- Influenza (flu): More severe than cold, includes high fever, body aches, fatigue
- COVID-19: Respiratory symptoms, fever, loss of taste/smell
- Gastroenteritis: Viral stomach flu - nausea, vomiting, diarrhea
- Mononucleosis: Fatigue, sore throat, fever, swollen lymph nodes

Management:
- Rest and hydration
- Over-the-counter symptom relief (pain relievers, decongestants)
- Antiviral medications for specific viruses (influenza, COVID-19)
- Isolation to prevent spread
- Seek medical attention if symptoms worsen or persist

Prevention: Hand hygiene, vaccination when available, avoiding close contact when sick.
"""
    },

    {
        "title": "Emergency Recognition - When to Seek Help",
        "category": "emergency",
        "content": """
Recognizing medical emergencies can save lives. Call emergency services (1122/115 in Pakistan) immediately for:

Cardiac emergencies:
- Chest pain or pressure lasting > 5 minutes
- Severe shortness of breath
- Fainting or loss of consciousness
- Rapid or irregular heartbeat with chest pain

Neurological emergencies:
- Sudden severe headache with confusion or seizures
- Stroke symptoms: facial drooping, arm weakness, speech difficulty
- Sudden vision loss or double vision
- Severe dizziness or loss of balance

Respiratory emergencies:
- Difficulty breathing or wheezing
- Blue lips or fingernails
- Coughing up blood

Trauma emergencies:
- Severe bleeding that won't stop
- Suspected broken bones with deformity
- Head injury with confusion or vomiting
- Burns covering large areas

Other emergencies:
- Severe allergic reactions (difficulty breathing, swelling)
- Poisoning or overdose
- Severe abdominal pain with vomiting
- High fever in infants < 3 months
- Suicidal thoughts or severe depression

Remember: When in doubt, call emergency services. It's better to be safe than sorry.
"""
    },

    {
        "title": "Pediatric Care - Children's Health Considerations",
        "category": "pediatric",
        "content": """
Children's health requires special consideration as they can deteriorate quickly and may not communicate symptoms clearly.

Infant care (< 1 year):
- Any fever in infants < 3 months requires immediate medical evaluation
- Normal temperature varies by age (rectal: 97.9-100.4°F, axillary: 97.5-99.1°F)
- Monitor for dehydration signs: dry diapers, sunken fontanelle, lethargy
- Vaccination schedule critical for disease prevention

Child care (1-12 years):
- Fever > 102°F (38.9°C) for > 3 days needs evaluation
- Ear infections common - may cause balance problems, hearing changes
- Growth and development monitoring important
- Immunizations protect against serious diseases

Adolescent care:
- Mental health concerns increasing
- Eating disorders, depression, anxiety common
- Substance use education important
- Reproductive health education

General pediatric advice:
- Regular well-child visits
- Healthy diet and physical activity
- Adequate sleep for age
- Safety measures (car seats, helmets, supervision)
- Early intervention for developmental concerns
"""
    },

    {
        "title": "Women's Health - Reproductive and Hormonal",
        "category": "womens_health",
        "content": """
Women's health encompasses reproductive health, hormonal changes, and gender-specific conditions.

Menstrual health:
- Normal cycle: 21-35 days, lasting 2-7 days
- Heavy bleeding: > 7 days or soaking > 1 pad/hour
- Irregular periods may indicate hormonal imbalance, stress, thyroid issues
- Severe pain (dysmenorrhea) may need evaluation

Reproductive health:
- Regular gynecological exams starting at age 21 or when sexually active
- Pap smears every 3 years (ages 21-65) or HPV testing
- Breast self-exams and mammograms as recommended
- Contraceptive counseling

Pregnancy care:
- Prenatal care starts early
- Warning signs: severe vomiting, bleeding, severe headache, decreased fetal movement
- Postpartum depression affects 10-20% of women

Menopause:
- Natural transition usually 45-55 years
- Symptoms: hot flashes, night sweats, mood changes, sleep disturbance
- Bone health monitoring important
- Hormone therapy may be considered for severe symptoms

Women's health emphasizes prevention, early detection, and comprehensive care.
"""
    },

    {
        "title": "Geriatric Care - Elderly Health Considerations",
        "category": "geriatric",
        "content": """
Older adults have unique health considerations due to age-related changes and multiple chronic conditions.

Age-related changes:
- Decreased sense of taste/smell affects nutrition
- Reduced kidney function affects medication dosing
- Thinner skin more susceptible to injury
- Decreased immune response increases infection risk
- Bones become more brittle (osteoporosis risk)

Common geriatric concerns:
- Polypharmacy (multiple medications) - drug interactions
- Falls - leading cause of injury
- Dementia and cognitive changes
- Urinary incontinence
- Chronic pain management
- Social isolation and depression

Preventive care:
- Annual comprehensive geriatric assessment
- Medication review by pharmacist
- Fall risk assessment and prevention
- Immunizations (flu, pneumonia, shingles)
- Cancer screenings appropriate for age
- Bone density testing
- Vision and hearing evaluations

Management focuses on maintaining independence, managing multiple conditions, and improving quality of life.
"""
    },

    {
        "title": "Nutrition and Wellness - Healthy Living",
        "category": "wellness",
        "content": """
Nutrition and lifestyle play crucial roles in maintaining health and preventing disease.

Balanced diet principles:
- Variety of fruits and vegetables (5+ servings daily)
- Whole grains over refined grains
- Lean proteins (fish, poultry, beans, nuts)
- Healthy fats (olive oil, avocados, nuts)
- Limited processed foods, added sugars, saturated fats
- Adequate calcium and vitamin D for bone health
- Hydration: 8+ glasses of water daily

Physical activity:
- 150 minutes moderate aerobic activity per week
- Muscle-strengthening activities 2+ days/week
- Daily movement breaks reduce sedentary time
- Activities adapted to fitness level and medical conditions

Sleep hygiene:
- 7-9 hours nightly for adults
- Consistent sleep schedule
- Dark, cool, quiet sleep environment
- Limit screen time before bed
- Address sleep disorders

Stress management:
- Regular relaxation techniques (meditation, deep breathing)
- Social connections and support systems
- Hobbies and enjoyable activities
- Professional help for chronic stress or anxiety

Preventive screenings:
- Blood pressure checks
- Cholesterol and diabetes screening
- Cancer screenings based on age and risk
- Vision and dental exams
- Immunizations

Wellness is proactive health management through healthy choices and regular medical care.
"""
    }
]

# Helper functions
def get_documents_by_category(category: str) -> List[Dict[str, str]]:
    """Get all documents in a specific category"""
    return [doc for doc in MEDICAL_DOCUMENTS if doc.get("category") == category]

def get_all_document_texts() -> List[str]:
    """Get all document texts for indexing"""
    return [doc["content"] for doc in MEDICAL_DOCUMENTS]

def get_document_titles() -> List[str]:
    """Get all document titles"""
    return [doc["title"] for doc in MEDICAL_DOCUMENTS]

def search_documents_by_keyword(keyword: str) -> List[Dict[str, str]]:
    """Search documents containing a keyword"""
    keyword_lower = keyword.lower()
    return [doc for doc in MEDICAL_DOCUMENTS
            if keyword_lower in doc["title"].lower() or keyword_lower in doc["content"].lower()]