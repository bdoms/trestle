<header>
    <h1>Site Name</h1>
</header>

<nav>
    <ul>
        <li><a href="/svelte/home">Home</a></li>
        <li><a href="/svelte/account">Account Settings</a></li>
        <li>
            <a on:click|preventDefault="{logOut}" href="#">Log Out</a>
            <form id="logout-form" method="post" action="/account/logout">
                <input type="hidden" name="_xsrf"/>
            </form>
        </li>
    </ul>
</nav>

<main>
    {#if loading}
        <p>Loading...</p>
    {:else}
        <svelte:component this={cmp} current_user={current_user}/>
    {/if}
</main>


<script>
    import {onMount} from 'svelte';
    import page from 'page';
    import utils from './utils';

    let current_user = {};
    let loading = true;

    $: logged_in = Object.keys(current_user).length > 0;

    onMount(async function() {
        // this is only triggered on the first page load - but loadPage is triggered once below BEFORE this
        utils.ajax('POST', '/home', {}, function(data) {
            current_user = data.user;
            loading = false;
        });
    });

    let logOut = function() {
        var form = document.getElementById('logout-form');
        if (!form.disabled) {
            // prevent multiple submits
            form.disabled = true;

            // make sure to clear these before redirecting away from the page
            form._xsrf.value = utils.XSRF;
            form.submit();
        }
    };

    // -- setup routing --
    export let routes;

    // allows for direct nav to load up the correct page initially
    let cmp_path = document.location.pathname;

    // this is reactive and will replace the component whenever it changes
    $: cmp = routes[cmp_path];

    var loadPage = function(ctx) {
        // do any generic page loading we have to here
        cmp_path = ctx.pathname;
    };

    for (var path in routes) {
        if (routes.hasOwnProperty(path)) {
            page(path, loadPage);
        }
    }
    page(); // register bindings
</script>
