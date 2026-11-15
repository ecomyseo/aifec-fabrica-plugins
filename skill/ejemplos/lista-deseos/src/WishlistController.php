<?php
/**
 * AIFEC — Lista de deseos: las tres pantallas de la tienda (ver la lista, guardar un producto y quitarlo).
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

namespace Plugins\ListaDeseos;

use Aifec\Kernel\App;
use Aifec\Kernel\HttpError;
use Aifec\Kernel\Request;
use Aifec\Kernel\Response;

/**
 * Todas las rutas pasan por los intermediarios «customer» (sin haber entrado, a la pantalla de entrada) y «csrf» (los
 * envíos solo desde la propia web). Un cliente solo ve y cambia SU lista: el id sale de la sesión, nunca de la petición.
 */
final class WishlistController
{
    /** @var App */
    private $app;

    /** @var Wishlist */
    private $wishlist;

    public function __construct(App $app)
    {
        $this->app = $app;
        $this->wishlist = new Wishlist($app);
    }

    /**
     * @param array<string,string> $params
     */
    public function index(Request $request, array $params): Response
    {
        $customerId = $this->customerId();
        $url = $this->app->url();
        $flash = $this->app->session('customer')->pullFlash();
        $data = [
            'page' => [
                'title' => t('My wish list'), 'type' => 'account', 'robots' => 'noindex, nofollow', 'body_class' => 'af-account',
                'canonical' => $url->origin() . $url->to($request->path),
            ],
            'products' => $this->wishlist->products($customerId),
            'message' => isset($flash['message']) && is_string($flash['message']) ? $flash['message'] : '',
            'max' => $this->wishlist->max(),
        ];

        return $this->private($this->app->render('lista-deseos::front/list', $data));
    }

    /**
     * @param array<string,string> $params id (del producto)
     */
    public function add(Request $request, array $params): Response
    {
        $productId = isset($params['id']) ? (int) $params['id'] : 0;
        $result = $this->wishlist->add($this->customerId(), $productId);
        if ($result === 'unknown') {
            throw HttpError::notFound();
        }
        $this->app->session('customer')->flash('message', $result === 'full'
            ? t('Your wish list is full: remove a product to save another one')
            : t('Saved in your wish list'));

        return $this->private(Response::redirect($this->app->url()->route('lista_deseos.list'), 303));
    }

    /**
     * @param array<string,string> $params id (del producto)
     */
    public function remove(Request $request, array $params): Response
    {
        $this->wishlist->remove($this->customerId(), isset($params['id']) ? (int) $params['id'] : 0);
        $this->app->session('customer')->flash('message', t('Removed from your wish list'));

        return $this->private(Response::redirect($this->app->url()->route('lista_deseos.list'), 303));
    }

    /** El cliente que ha entrado, de la sesión. Sin sesión, 401 (el intermediario «customer» ya lo habrá mandado a entrar). */
    private function customerId(): int
    {
        $id = $this->app->auth()->customerId();
        if ($id === null) {
            throw HttpError::forbidden('Sign in to continue');
        }

        return (int) $id;
    }

    private function private(Response $response): Response
    {
        $response->headers['Cache-Control'] = 'no-store, private';
        $response->headers['X-Robots-Tag'] = 'noindex, nofollow';

        return $response;
    }
}
