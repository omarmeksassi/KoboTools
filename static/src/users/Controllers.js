(function ($, undefined) {

    angular
        .module('koboTools')
        .controller('UserController',
        UserController
    );

    angular
        .module('koboTools')
        .controller('AppController',
        AppController
    );

    function UserController($mdSidenav, $mdBottomSheet, $log, $q, $scope) {
    }

    function AppController($mdSidenav, $mdBottomSheet, $timeout, $q, $http, $scope) {
        var self = this;

        self.loadForms = loadForms;
        self.downloadData = downloadData;

        self.user = {
            username: '',
            password: ''
        };

        self.formAction = "";


        function loadForms() {
            var authRequest;
            if (!self.user.token) {
                authRequest = $http.post('/fetch-token', {username: self.user.username, password: self.user.password}).then(function (d) {
                    self.user.token = d.data.token;
                }).catch(function () {
                    alert('Invalid username or password.');
                });
            } else {
                authRequest = $q.when(true);
            }

            authRequest.then(function () {
                return $http.post('/fetch-forms', self.user).then(function (d) {
                    self.forms = d.data;
                });
            });
        }


        function downloadData(pk) {
            self.formAction = '/download-data/' + pk;
            $timeout(function () {
                $('form[name=downloadForm]').submit();
            }, 100);
        }
    }

})(jQuery);
