<svelte:head>
	<title>Change Email</title>
</svelte:head>

<h2>Change Email</h2>

<form action="/user/email" method="post" on:submit|preventDefault="{changeEmail}">
    <input type="hidden" name="_xsrf"/>

    {#if errors.match}
        <p class="error">Invalid current password. Please try again.</p>
    {/if}
    {#if errors.exists}
        <p class="error">That email address is already in use.</p>
    {/if}

    <p>
        <label for="password">Current Password</label>
        <input type="password" name="password" id="password" required autofocus />
        {#if errors.password}
            <span class="error">Please enter a valid password.</span>
        {/if}
    </p>

    <p>
        <label for="email">Email</label>
        <input type="email" name="email" id="email" required value="{current_user ? current_user.email : ''}"/>
        {#if errors.email}
            <span v-if="errors.email" class="error">Please enter a valid email.</span>
        {/if}
        {#if success.ok}
            <span class="success">Saved</span>
        {/if}
    </p>

    <p><input type="submit" value="Change Email" /></p>
</form>


<script>
    import utils from './utils';

    export let current_user;

    let errors = {};
    let success = {};

    let changeEmail = function(e) {
        // doing it this way creates a closure around the component properties
        // which means they get updated reactively when modified in the other non-component code
        // the alternatives are
        //   1) setting up subscriptions here and firing events in the util function
        //   2) using a store
        utils.submitForm(this, function(error_data, success_data) {
            errors = error_data;
            success = success_data;

            if (success.ok) {
                // we want to update the value, but we do not want it to be reactive with the form input
                // that's in case the user never actually submits the form, or there's an error
                current_user.email = document.getElementById('email').value;
            }
        });
    };
</script>
    