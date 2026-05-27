# -*- coding: utf-8 -*-

{
    'name': 'Kacel Sante',
    'version': '17.0.1.0.0',
    'summary': """CENTRE DE MEDECIN PHYSIQUE ET DE READAPTATION FONCTIONNELLE""",
    'author': 'AZ Automation',
    'company': 'AZ Automation Solutions',
    'depends': ['base','web','mail'],
    'data': [
         'security/medical_security.xml',
         'security/ir.model.access.csv',
         'views/caisse_abonnement.xml',
         'views/patient_views.xml',
         'views/gestion_abonnement.xml',
         'reports/gestion_abonnement_report.xml',
         'views/kinesitherapy_act_views.xml',
         'views/planing_sex_views.xml',
         'views/caisse_views.xml',
         'wizard/transfer_wizard.xml',
         'wizard/pay_act_wizard.xml',
         'data/ir_sequence_data.xml',
         'views/medical_doctor_views.xml',
         'views/medical_appointment_views.xml',
         'views/patient_act_session_views.xml',
         'views/kinesitherapy_appointment.xml',
         'views/act_practice_count.xml',
         'views/banliotherapie_appointment.xml',
         'views/caisse_views_banliotherapie.xml',
         'views/gestion_tarif.xml',
         'views/planning_slot.xml',
         'views/service_intensif_views.xml',
         'views/kinesitherapist_view.xml',
         'views/planing_kines_view.xml',
         'views/menu_views.xml',
         'views/pack.xml',
         'views/patient_act_session_views.xml',

    ],

'assets': {
    'web.assets_backend': [
        # 'kacel_sante/static/src/js/moment.js',  # Manually include the moment library
        #  'kacel_sante/static/src/js/calendar_view_override.js',  # Your custom JS file
        #  'kacel_sante/static/src/js/test.js',  # Test file
    ],
},
    'images': ['static/description/Kacel_logo.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
