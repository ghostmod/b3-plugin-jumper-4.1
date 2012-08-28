CREATE TABLE IF NOT EXISTS `maps_records` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `client_id` int(10) unsigned NOT NULL,
  `map` varchar(64) NOT NULL,
  `time` int(10) unsigned NOT NULL,
  `time_add` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM  DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;