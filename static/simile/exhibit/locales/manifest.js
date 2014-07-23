Exhibit.jQuery(document).bind("registerLocales.exhibit", function() {
    Exhibit.jQuery(document).trigger("beforeLocalesRegistered.exhibit");
    new Exhibit.Locale("default", Exhibit.urlPrefix + "locales/en/locale.js");
    new Exhibit.Locale("en", Exhibit.urlPrefix + "locales/en/locale.js");
    Exhibit.jQuery(document).trigger("localesRegistered.exhibit");
});
