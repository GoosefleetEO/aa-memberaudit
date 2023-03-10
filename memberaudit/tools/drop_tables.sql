-- Deletes all Member Audit tables from the database
SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS memberaudit_character;
DROP TABLE IF EXISTS memberaudit_characterasset;
DROP TABLE IF EXISTS memberaudit_characterattributes;
DROP TABLE IF EXISTS memberaudit_charactercontact;
DROP TABLE IF EXISTS memberaudit_charactercontact_labels;
DROP TABLE IF EXISTS memberaudit_charactercontactlabel;
DROP TABLE IF EXISTS memberaudit_charactercontract;
DROP TABLE IF EXISTS memberaudit_charactercontractbid;
DROP TABLE IF EXISTS memberaudit_charactercontractitem;
DROP TABLE IF EXISTS memberaudit_charactercorporationhistory;
DROP TABLE IF EXISTS memberaudit_characterdetails;
DROP TABLE IF EXISTS memberaudit_characterdoctrineshipcheck;
DROP TABLE IF EXISTS memberaudit_characterdoctrineshipcheck_insufficient_skills;
DROP TABLE IF EXISTS memberaudit_characterimplant;
DROP TABLE IF EXISTS memberaudit_characterjumpclone;
DROP TABLE IF EXISTS memberaudit_characterjumpcloneimplant;
DROP TABLE IF EXISTS memberaudit_characterlocation;
DROP TABLE IF EXISTS memberaudit_characterloyaltyentry;
DROP TABLE IF EXISTS memberaudit_charactermail;
DROP TABLE IF EXISTS memberaudit_charactermail_labels;
DROP TABLE IF EXISTS memberaudit_charactermailinglist;
DROP TABLE IF EXISTS memberaudit_charactermaillabel;
DROP TABLE IF EXISTS memberaudit_charactermailmaillabel;
DROP TABLE IF EXISTS memberaudit_characterminingledgerentry;
DROP TABLE IF EXISTS memberaudit_character_mailing_lists;
DROP TABLE IF EXISTS memberaudit_charactermail_recipients;
DROP TABLE IF EXISTS memberaudit_charactermailunreadcount;
DROP TABLE IF EXISTS memberaudit_characteronlinestatus;
DROP TABLE IF EXISTS memberaudit_characterskill;
DROP TABLE IF EXISTS memberaudit_characterskillpoints;
DROP TABLE IF EXISTS memberaudit_characterskillqueueentry;
DROP TABLE IF EXISTS memberaudit_characterupdatestatus;
DROP TABLE IF EXISTS memberaudit_characterwalletbalance;
DROP TABLE IF EXISTS memberaudit_characterwalletjournalentry;
DROP TABLE IF EXISTS memberaudit_characterwallettransaction;
DROP TABLE IF EXISTS memberaudit_doctrine;
DROP TABLE IF EXISTS memberaudit_doctrine_ships;
DROP TABLE IF EXISTS memberaudit_doctrineship;
DROP TABLE IF EXISTS memberaudit_doctrinerecommendedshipskill;
DROP TABLE IF EXISTS memberaudit_doctrinerequiredshipskill;
DROP TABLE IF EXISTS memberaudit_doctrineshipskill;
DROP TABLE IF EXISTS memberaudit_location;
DROP TABLE IF EXISTS memberaudit_mailentity;
DROP TABLE IF EXISTS memberaudit_characterskillsetcheck;
DROP TABLE IF EXISTS memberaudit_characterskillsetcheck_failed_recommended_skills;
DROP TABLE IF EXISTS memberaudit_characterskillsetcheck_failed_required_skills;
DROP TABLE IF EXISTS memberaudit_skillset;
DROP TABLE IF EXISTS memberaudit_skillsetgroup;
DROP TABLE IF EXISTS memberaudit_skillsetgroup_skill_sets;
DROP TABLE IF EXISTS memberaudit_skillsetskill;
DROP TABLE IF EXISTS memberaudit_charactership;
DROP TABLE IF EXISTS memberaudit_compliancegroupdesignation;
SET FOREIGN_KEY_CHECKS=1;
