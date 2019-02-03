odoo.define('flexipharmacy.customer_display', function (require) {
"use strict";

	require('bus.BusService');
//	var bus = require('bus.Longpolling');
	var Widget = require('web.Widget');
	var session = require('web.session');
	var rpc = require('web.rpc');
	var core = require('web.core');
	var utils = require('web.utils');
	var field_utils = require('web.field_utils');
	var round_di = utils.round_decimals;

	var _t = core._t;
	var QWeb = core.qweb;

	var CustomerDisplayWidget = Widget.extend({
		init:function(parent,options){
			this._super(parent);
			this.company_id = session.company_id;
			this.config_id = Number(odoo.config_id);
			this.image_interval = false;
			this.set_customer = false;
			this.advertise_data = false;
			this.enable_customer_rating = false;
			this.load_config();
			this.load_customer_display_data();
			this.load_currency();
		},
		load_config: function(){
			var self = this;
			if(this.config_id){
				var params = {
	        		model: 'customer.display',
	        		method: 'load_config',
	        		args: [self.config_id],
	        	}
	        	rpc.query(params, {async: false})
	            .then(function(pos_config){
	            	if(pos_config && pos_config[0]){
	            		self.image_interval = pos_config[0].image_interval || 0;
	            		self.enable_customer_rating = pos_config[0].enable_customer_rating || false;
	            		self.set_customer = pos_config[0].set_customer || false;
	            	}
	            });
			}
		},
		load_customer_display_data: function(){
			var self = this;
			var params = {
        		model: 'customer.display',
        		method: 'load_customer_display_data',
        		args: [self.config_id],
        	}
        	rpc.query(params, {async: false})
            .then(function(advertise_data){
            	if(advertise_data && advertise_data[0]){
            		self.advertise_data = advertise_data;
            	}
            });
		},
		load_currency: function(){
	    	var self = this;
	    	var params = {
        		model: 'customer.display',
        		method: 'load_currency',
        		args: [self.company_id],
        	}
        	rpc.query(params, {async: false})
            .then(function(currency){
            	if(currency && currency[0]){
            		self.currency = currency[0];
            		if (self.currency.rounding > 0 && self.currency.rounding < 1) {
                        self.currency.decimals = Math.ceil(Math.log(1.0 / self.currency.rounding) / Math.log(10));
                    } else {
                        self.currency.decimals = 0;
                    }
            	}
            });
	    },
		format_currency: function(amount,precision){
	    	var self = this;
	        var currency = (self && self.currency) ? self.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
	        amount = this.format_currency_no_symbol(amount,precision);
	        if (currency.position === 'after') {
	            return amount + ' ' + (currency.symbol || '');
	        } else {
	            return (currency.symbol || '') + ' ' + amount;
	        }
	    },
	    format_currency_no_symbol: function(amount, precision) {
	    	var self = this;
	        var currency = (self && self.currency) ? self.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
	        var decimals = currency.decimals;
	        if (typeof amount === 'number') {
	            amount = round_di(amount,decimals).toFixed(decimals);
	            amount = field_utils.format.float(round_di(amount, decimals), {digits: [69, decimals]});
	        }
	        return amount;
	    },
	});

	var CustomerDisplayScreen = CustomerDisplayWidget.extend({
	    template: 'CustomerDisplayScreen',
	    events: {
	        'click .stars span': 'send_rating',
	        'click .create_customer':'create_customer',
	    },

	    init: function() {
	    	var self = this;
	        this._super(arguments[0],{});
	        this.customer_name = false;
	        self.company_logo = window.location.origin+"/web/binary/company_logo?db=pos_customer_screen_v11&company="+self.company_id;
	    },
	    start: function(){
	    	this._super();
	    	var self = this;
//	    	Left Panel
    		this.left_panel = new LeftPanelWidget(this, {});
	        this.left_panel.replace(this.$('.placeholder-LeftPanelWidget'));
//	        Right Panel
    		this.right_panel = new RightPanelWidget(this, {});
	        this.right_panel.replace(this.$('.placeholder-RightPanelWidget'));
	        self.call('bus_service', 'updateOption','customer.display',session.uid);
	        self.call('bus_service', 'onNotification', self, self._onNotification);
	    	self.call('bus_service', 'startPolling');
	    	setTimeout(function(){
	    		self.render_customer();
	    	},100);
	    },
	    _onNotification: function(notifications){
	    	var self = this;
	    	for (var notif of notifications) {
	    		if(notif[1].customer_display_data){
	    			var user_id = notif[1].customer_display_data.user_id;
	    			var cart_data = notif[1].customer_display_data.cart_data;
	    			var customer_name = notif[1].customer_display_data.customer_name;
	    			self.customer_name = customer_name;
	    			self.render_customer();
	                self.left_panel.update_cart_data(cart_data);
	                var order_total = notif[1].customer_display_data.order_total;
	                var change_amount = notif[1].customer_display_data.change_amount;
	                var payment_info = notif[1].customer_display_data.payment_info;
	                self.right_panel.update_data(order_total, change_amount, payment_info);
	                self.scroll_down();
	                if(notif[1].customer_display_data.new_order){
                        $('.stars span').removeClass("checked");
	    			}
	    		}
	    	}
	    },
	    send_rating: function(event){
	        var self = this;
	        var rating_val = $(event.currentTarget).attr('val');
	        $('.stars span').removeClass("checked");
	        for(var i= 0;i<rating_val;i++ ){
	            $('.stars span')[i].className += " checked";
	        }
	        var params = {
                model: 'customer.display',
                method: 'send_rating',
                args: [self.config_id, rating_val],
            }
            rpc.query(params, {async: false}).then(function(result){});
	    },
	    create_customer: function(event){
	        var self = this;
	    	this.close_popover();
	    	if(!$(".popover").is(":visible")){
	    		$(event.currentTarget).popover({
		    	    placement: 'bottom',
		    	    title: 'Create Customer <i class="fa fa-times close_popover" aria-hidden="true" style="float:right"></i>',
		    	    html: true,
		    	    content: function() {
		    	    	return QWeb.render('CreateCustomer');
		    	    },
		    	});
		    	$(event.currentTarget).popover('show');
                $('button.search_client').click(function(){
	    	        self.search_customer();
	    	    });
	    	    $('#customer_mobile').keypress(function(e){
	    	        self.keypress_customer_mobile(e);
	    	    });
	    	    $('#customer_email').keyup(function(e){
	    	        self.keyup_customer_email(e);
	    	    });
	    	    $('button.create_client').click(function(){
	    	        self.submit_create_client();
	    	    });
		    	$('i.close_popover').click(function(){
		    		$(event.currentTarget).popover('dispose');
	            });
	    	}
	    },
	    search_customer: function(){
	        var self = this;
	        var customer_mobile = ($('#customer_mobile').val());
	        if(customer_mobile){
	             var params = {
                    model: 'customer.display',
                    method: 'search_customer',
                    args: [customer_mobile, self.config_id],
                }
                rpc.query(params, {async: false})
                .then(function(result){
                    if(result){
                        self.close_popover();
                    } else{
                    	$('#customer_name').focus();
                    }
                });
	        }
	    },
	    close_popover: function(){
        	$(".popover").popover('dispose');
        },
	    keypress_customer_mobile: function(e){
	    	if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
	            return false;
	        }
	    },
	    keyup_customer_email: function(e){
	    	var self = this;
	    	var value = $(e.currentTarget).val();
	        var valid = self.validateEmail(value);
	        if (!valid) {
	            $(e.currentTarget).css('color', 'red');
	            $(e.currentTarget).attr('valid_email',false);
	        } else {
	        	$(e.currentTarget).css('color', '#555');
	        	$(e.currentTarget).attr('valid_email',true);
	        }
	    },
	    validateEmail: function(value){
	    	var emailPattern = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/;
	        return emailPattern.test(value);
	    },
	    submit_create_client: function(){
	    	var self = this;
	    	var email = $('#customer_email').val();
	    	var valid_email = $('#customer_email').attr('valid_email');
	    	var customer_mobile = ($('#customer_mobile').val());
	    	var customer_name = $('#customer_name').val();
	    	if(customer_name){
	    		if(customer_mobile){
	    			if(email && valid_email == "false"){
	    				alert("Please enter valid email");
	    				$('#customer_email').focus();
	    			}else{
	    				var params = {
    		        		model: 'customer.display',
    		        		method: 'search_create_customer',
    		        		args: [customer_name, email, customer_mobile, self.config_id],
    		        	}
    		        	rpc.query(params, {async: false})
    		            .then(function(result){
    		                if(result){
                                self.close_popover();
                            }
    		            });
	    			}
	    		}else{
	    			alert("Customer mobile number is required!");
	    			$('#customer_mobile').focus();
	    		}
	    	}else{
	    		alert("Customer name is required!");
	    		$('#customer_name').focus();
	    	}
	    },
	    scroll_down: function(){
	    	var scrl_height = 0;
            $(".order-scroller").prop('scrollHeight');
            scrl_height = $(".order-scroller").prop('scrollHeight');
            if(scrl_height){
        	    $(document).find(".order-scroller").scrollTop(scrl_height);
            } else{
        	    $(document).find(".order-scroller").scrollTop($(document).find(".order-scroller").prop('scrollHeight'));
            }
	    },
	    render_customer: function(){
	       	var self = this;
	       	var el_customer_name = QWeb.render('CustomerName',{
	       		widget: self,
	       		customer_name:self.customer_name,
	       	});
           $('.client_name').html(el_customer_name);
           var set_customer = true;
           if(self.customer_name == "Unknown" || self.customer_name == false){
        	   	set_customer = false;
           }
           var CreateCustomer = QWeb.render('CreateCustomer',{
    	   customer_name:self.customer_name,
    	   set_customer: set_customer,
	               });
	               $('.create_customer_details').html('');
	               $('.create_customer_details').html(CreateCustomer);
       },
	    render_customer: function(){
	    	var self = this;
	    	var el_customer_name = QWeb.render('CustomerName',{
	    		customer_name:self.customer_name,
				widget: self,
            });
            $('.client_name').html(el_customer_name);
	    },
	});

	var LeftPanelWidget = CustomerDisplayWidget.extend({
		template: 'LeftPanelWidget',
		init: function(){
			var self = this;
	        this._super(arguments[0],{});
	        this.cart_data = false;
		},
		replace: function($target){
			this.renderElement();
			var target = $target[0];
			target.parentNode.replaceChild(this.el,target);
		},
		renderElement: function(){
			var self = this;
			self.origin = session.origin;
			var el_str = QWeb.render(this.template, {
				widget: this, 
				cart_data:this.cart_data,
			});
			var el_node = document.createElement('div');
			el_node.innerHTML = el_str;
			el_node = el_node.childNodes[1];
			if(this.el && this.el.parentNode){
				this.el.parentNode.replaceChild(el_node,this.el);
			}
			this.el = el_node;
		},
		update_cart_data: function(cart_data){
			this.cart_data = cart_data
			this.renderElement();
		},
	});

	var RightPanelWidget = CustomerDisplayWidget.extend({
		template: 'RightPanelWidget',
		init: function(){
			var self = this;
	        this._super(arguments[0],{});
	        self.order_amount = 0;
            self.change_amount = 0;
            self.payment_info = [];
		},
		replace: function($target){
			this.renderElement();
			var target = $target[0];
			target.parentNode.replaceChild(this.el,target);
		},
		update_data: function(order_total, change_amount, payment_info){
			var self = this;
			self.order_amount = order_total;
            self.change_amount = change_amount;
            self.payment_info = payment_info;
            var payment_details = QWeb.render('Payment-Details',{ 
                widget:  self,
            });
            $('.pos-payment_info_details').html(payment_details);
            var paymentline_details = QWeb.render('Paymentlines-Details',{ 
                widget:  self,
            });
            $('.paymentline-details').html(paymentline_details);
		},
		renderElement: function(){
			var self = this;
			self.origin = session.origin;
			var el_str = QWeb.render(this.template, {
				widget: this,
				order_amount: self.order_amount,
				change_amount: self.change_amount,
				payment_info:self.payment_info,
			});
			var el_node = document.createElement('div');
			el_node.innerHTML = el_str;
			el_node = el_node.childNodes[1];
			if(this.el && this.el.parentNode){
				this.el.parentNode.replaceChild(el_node,this.el);
			}
			this.el = el_node;
			setTimeout(function(){
				self.start_slider();
			},100)
		},
		start_slider: function(){
			var time = this.image_interval * 1000;
			var slideCount = $('#slider ul li').length;
			var slideWidth = $('#slider ul li').width();
			var slideHeight = $('#slider ul li').height();
			var sliderUlWidth = slideCount * slideWidth;
			$('#slider').css({ width: slideWidth, height: slideHeight });
			$('#slider ul').css({ width: sliderUlWidth, marginLeft: - slideWidth });
		    $('#slider ul li:last-child').prependTo('#slider ul');
		    function moveLeft() {
		        $('#slider ul').animate({
		            left: + slideWidth
		        }, 200, function () {
		            $('#slider ul li:last-child').prependTo('#slider ul');
		            $('#slider ul').css('left', '');
		        });
		    };
		    function moveRight() {
		        $('#slider ul').animate({
		            left: - slideWidth
		        }, 200, function () {
		            $('#slider ul li:first-child').appendTo('#slider ul');
		            $('#slider ul').css('left', '');
		        });
		    };
		    $('a.control_prev').click(function (e) {
		    	e.stopImmediatePropagation();
		        moveLeft();
		    });
		    $('a.control_next').click(function (e) {
		    	e.stopImmediatePropagation();
		        moveRight();
		    });
		    setInterval(function(){
		    	$('a.control_next').trigger('click');
		    }, time);
		},
	});

	core.action_registry.add('customer_display.ui', CustomerDisplayScreen);
});