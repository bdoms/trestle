<svelte:head>
	<title>Active Sessions</title>
</svelte:head>

<h2>Active Sessions</h2>

<table>
    <thead>
        <tr>
            <th>Device</th>
            <th>IP Address</th>
            <th>Last Login</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
    {#each auths as auth, index}
        <tr>
            <td>
                {#if auth.device || auth.os || auth.browser}
                    {#if auth.device}
                        {auth.device}
                    {:else}
                        {auth.os}
                    {/if}
                    {auth.browser}
                {:else}
                    {auth.user_agent}
                {/if}
            </td>
            <td>{auth.ip}</td>
            <td>
                <time datetime="{auth.modified_dt}">
                    {utils.formatDateTime(auth.modified_dt)}
                </time>
            </td>
            <td>
                {#if auth.slug == current_auth_id}
                    Current Session
                {:else}
                    <form action="/user/auths" method="post" on:submit|preventDefault="{() => revokeAccess(event, index)}">
                        <input type="hidden" name="_xsrf"/>
                        <input type="hidden" name="auth_key" value="{auth.slug}" />
    
                        <input type="submit" value="Revoke Access" />
                    </form>
                {/if}
            </td>
        </tr>
    {/each}
    </tbody>
</table>


<script>
    import {onMount} from 'svelte';
    import utils from './utils';

    export let current_user;

    let auths = [];
    let current_auth_id = '';

    onMount(async function() {
        trestle.ajax('GET', '/user/auths?app=1', {}, function(data) {
            auths = data.auths;
            current_auth_id = data.current_auth_id;
        });
    });

    let revokeAccess = function(e, index) {
        var form = e.target;
        var form_data = utils.getFormData(form);
        trestle.ajax('POST', form.action + '?app=1', form_data, function(data) {
            if (data.ok) {
                auths.splice(index, 1);
                auths = auths; // force reactivity
            }
        });
    };
</script>
    